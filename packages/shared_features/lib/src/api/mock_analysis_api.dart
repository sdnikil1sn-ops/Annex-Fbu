/// Explicit in-memory mock of the backend API for tests and local dev.
///
/// Implements [AnalysisApi] behind the same interface as the HTTP client
/// and simulates the async pipeline: submissions start `pending`, become
/// `processing`, then complete with a deterministic report (unless the
/// input is flagged to fail).
library;

import 'package:shared_models/shared_models.dart';

import 'analysis_api.dart';

/// A deterministic fake backend.
///
/// Optionally simulates provider failures: texts containing the
/// `failTrigger` substring complete with `failed` status.
class MockAnalysisApi implements AnalysisApi {
  MockAnalysisApi({
    this.failTrigger = '!!!',
    this.initialReport,
    this.delay = const Duration(milliseconds: 10),
  }) {
    _seedClass();
    _seedSources();
    _seedReviewQueue();
  }

  /// Substring that makes submitted text fail analysis.
  final String failTrigger;

  /// The report produced for successful analyses.
  final AnalysisReport? initialReport;

  /// Simulated processing latency per transition.
  final Duration delay;

  final List<Analysis> _analyses = [];
  final List<String> _inputs = [];
  final Map<String, DateTime> _completedLessons = {};
  int _nextId = 1;

  // Educator state (Phase 20): one seeded class owned by the mock caller
  // so the classes tab has content out of the box. Seeded eagerly so a
  // delete-class followed by a list refresh does not resurrect it.
  final List<ClassRoom> _classes = [];
  final Map<String, List<ClassMember>> _membersByClass = {};
  final Map<String, List<Assignment>> _assignmentsByClass = {};
  int _nextClassId = 1;
  int _nextAssignmentId = 1;

  // Translation contribution state (Phase 21): submitted suggestions keyed
  // by (locale, key) so re-submission updates the existing pending row.
  final Map<String, TranslationSuggestion> _mySuggestions = {};
  int _nextSuggestionId = 1;

  // Source registry state (Phase 22): the Phase 14 seed publishers plus
  // per-user community ratings (one voice per user per source).
  final Map<String, Source> _sourcesByDomain = {};
  final Map<String, Map<String, int>> _ratingsByDomain = {};

  // Moderator review queue (Phase 23): suggestions submitted by other
  // mock users, awaiting approve/reject.
  final List<TranslationSuggestion> _pendingQueue = [];

  /// Whether the last submission was recorded (test hook).
  String? lastSubmittedText;
  String? lastSubmittedImage;
  String? lastSubmittedLocale;

  static final _report = AnalysisReport(
    summary: 'The text makes two checkable claims with verifiable evidence.',
    claims: const [
      ClaimItem(text: 'The Earth orbits the Sun', verifiability: 0.95),
      ClaimItem(text: 'The claim cites an outdated study', verifiability: 0.45),
    ],
  );

  @override
  Future<Analysis> submitText(String text, {String locale = 'en'}) async {
    lastSubmittedText = text;
    lastSubmittedLocale = locale;
    await Future<void>.delayed(delay);
    final now = DateTime.now().toUtc();
    final analysis = Analysis(
      id: 'mock-${_nextId++}',
      inputType: AnalysisInputType.text,
      status: AnalysisStatus.pending,
      locale: locale,
      createdAt: now,
    );
    _analyses.add(analysis);
    _inputs.add(text);
    return analysis;
  }

  @override
  Future<Analysis> submitImage(String image, {String locale = 'en'}) async {
    lastSubmittedImage = image;
    lastSubmittedLocale = locale;
    await Future<void>.delayed(delay);
    final now = DateTime.now().toUtc();
    final analysis = Analysis(
      id: 'mock-${_nextId++}',
      inputType: AnalysisInputType.image,
      status: AnalysisStatus.pending,
      locale: locale,
      createdAt: now,
    );
    _analyses.add(analysis);
    _inputs.add('image');
    return analysis;
  }

  @override
  Future<Analysis> fetchAnalysis(String id) async {
    await Future<void>.delayed(delay);
    final index = _analyses.indexWhere((a) => a.id == id);
    if (index < 0) {
      throw const ApiException('analysis.not_found', 'Analysis not found');
    }
    final current = _analyses[index];
    if (current.status.isTerminal) return current;

    // Advance the simulated state machine: pending -> processing -> done.
    // Failure is driven by the input captured at submit time, so each
    // analysis is evaluated independently.
    final failed = _inputs[index].contains(failTrigger);
    final report = initialReport ??
        (current.inputType == AnalysisInputType.image
            ? _imageReport
            : _report);
    final updated = failed
        ? Analysis(
            id: current.id,
            inputType: current.inputType,
            status: AnalysisStatus.failed,
            locale: current.locale,
            failureReason: 'analysis.processing_failed',
            createdAt: current.createdAt,
            completedAt: DateTime.now().toUtc(),
          )
        : Analysis(
            id: current.id,
            inputType: current.inputType,
            status: AnalysisStatus.completed,
            locale: current.locale,
            report: report,
            createdAt: current.createdAt,
            completedAt: DateTime.now().toUtc(),
          );
    _analyses[index] = updated;
    return updated;
  }

  static final AnalysisReport _imageReport = AnalysisReport(
    summary:
        'The image shows a claim with checkable evidence; OCR text was extracted and forensics found no signs of tampering.',
    claims: const [
      ClaimItem(text: 'The poster attributes the claim to an official source', verifiability: 0.7),
      ClaimItem(text: 'The image shows signs of digital editing', verifiability: 0.25),
    ],
    media: MediaContext(
      inputType: 'image',
      mime: 'image/jpeg',
      sizeBytes: 24891,
      ocrText:
          'Breaking: officials confirm the announcement takes effect today.',
      ocrConfidence: 0.93,
      riskScore: 0.12,
      signals: const {'ela_score': 0.12, 'width': 1280, 'height': 720},
    ),
  );

  @override
  Future<List<Lesson>> fetchLessons({String locale = 'en'}) async {
    await Future<void>.delayed(delay);
    return _seed.map((lesson) {
      return Lesson(
        id: lesson.id,
        slug: lesson.slug,
        difficulty: lesson.difficulty,
        category: lesson.category,
        estimatedMinutes: lesson.estimatedMinutes,
        orderIndex: lesson.orderIndex,
        title: _localized(lesson, locale).title,
        summary: _localized(lesson, locale).summary,
        completed: _completedLessons.containsKey(lesson.id),
        completedAt: _completedLessons[lesson.id],
      );
    }).toList();
  }

  @override
  Future<Lesson> fetchLesson(String idOrSlug, {String locale = 'en'}) async {
    await Future<void>.delayed(delay);
    final lesson = _findLesson(idOrSlug);
    if (lesson == null) {
      throw const ApiException('lesson.not_found', 'Lesson not found');
    }
    final content = _localized(lesson, locale);
    return Lesson(
      id: lesson.id,
      slug: lesson.slug,
      difficulty: lesson.difficulty,
      category: lesson.category,
      estimatedMinutes: lesson.estimatedMinutes,
      orderIndex: lesson.orderIndex,
      title: content.title,
      summary: content.summary,
      completed: _completedLessons.containsKey(lesson.id),
      completedAt: _completedLessons[lesson.id],
      locale: content.locale,
      sections: content.sections,
    );
  }

  @override
  Future<LessonProgress> completeLesson(String idOrSlug) async {
    await Future<void>.delayed(delay);
    final lesson = _findLesson(idOrSlug);
    if (lesson == null) {
      throw const ApiException('lesson.not_found', 'Lesson not found');
    }
    // Idempotent: the first completion timestamp wins.
    final now = DateTime.now().toUtc();
    final completedAt = _completedLessons.putIfAbsent(lesson.id, () => now);
    return LessonProgress(lessonId: lesson.id, completedAt: completedAt);
  }

  // --- lesson internals --------------------------------------------------

  static const List<Lesson> _seed = [
    Lesson(
      id: '00000000-0000-4000-8000-000000000001',
      slug: 'spotting-misinformation',
      difficulty: 'beginner',
      category: 'media_literacy',
      estimatedMinutes: 5,
      orderIndex: 1,
    ),
    Lesson(
      id: '00000000-0000-4000-8000-000000000002',
      slug: 'understanding-credibility-scores',
      difficulty: 'intermediate',
      category: 'source_credibility',
      estimatedMinutes: 7,
      orderIndex: 2,
    ),
  ];

  static Lesson? _findLesson(String idOrSlug) {
    for (final lesson in _seed) {
      if (lesson.id == idOrSlug || lesson.slug == idOrSlug) return lesson;
    }
    return null;
  }

  /// Content keyed by (slug, locale); mirrors the seed migration — the
  /// first lesson has a pt variant, everything else falls back to en.
  static const Map<String, Map<String, _LessonContent>> _content = {
    'spotting-misinformation': {
      'en': _LessonContent(
        locale: 'en',
        title: 'Spotting Misinformation',
        summary:
            'Learn to recognize the common patterns behind misleading content.',
        sections: [
          LessonSection(
            heading: 'Why misinformation spreads',
            body:
                'Misinformation spreads faster than corrections because it is designed to be shared.',
            bullets: [
              'Emotional headlines are a red flag',
              'Check before you share',
            ],
          ),
          LessonSection(
            heading: 'The five-question check',
            body:
                'Before trusting a post, ask who published it and what evidence it carries.',
          ),
        ],
      ),
      'pt': _LessonContent(
        locale: 'pt',
        title: 'Como Detectar Desinformação',
        summary:
            'Aprenda a reconhecer os padrões comuns por trás de conteúdos enganosos.',
        sections: [
          LessonSection(
            heading: 'Por que a desinformação se espalha',
            body: 'A desinformação se espalha mais rápido que correções.',
            bullets: ['Títulos emocionais são um sinal de alerta'],
          ),
        ],
      ),
    },
    'understanding-credibility-scores': {
      'en': _LessonContent(
        locale: 'en',
        title: 'Understanding Credibility Scores',
        summary: 'How ANNEX scores sources and what the numbers mean.',
        sections: [
          LessonSection(
            heading: 'What a credibility score is',
            body:
                'A credibility score estimates how trustworthy a publisher is.',
          ),
        ],
      ),
    },
  };

  static _LessonContent _localized(Lesson lesson, String locale) {
    final byLocale = _content[lesson.slug] ?? const {};
    return byLocale[locale] ?? byLocale['en'] ?? const _LessonContent();
  }

  @override
  Future<ClassRoom> createClass(String name, String description) async {
    await Future<void>.delayed(delay);
    final id = 'c0000000-0000-4000-8000-0000000000${_nextClassId++}';
    final now = DateTime.now().toUtc();
    final room = ClassRoom(
      id: id,
      ownerId: 'mock-owner',
      name: name,
      description: description,
      inviteCode: _nextInviteCode(),
      role: 'teacher',
      createdAt: now,
    );
    _classes.add(room);
    _membersByClass[id] = [
      ClassMember(
        userId: 'mock-owner',
        role: 'teacher',
        displayName: 'Ms. Alvarez',
        joinedAt: now,
      ),
    ];
    _assignmentsByClass[id] = [];
    return room;
  }

  @override
  Future<List<ClassRoom>> fetchClasses() async {
    await Future<void>.delayed(delay);
    return List.unmodifiable(_classes);
  }

  @override
  Future<ClassRoom> fetchClass(String id) async {
    await Future<void>.delayed(delay);
    final room = _findClass(id);
    if (room == null) {
      throw const ApiException('class.not_found', 'Class not found');
    }
    final members = _membersByClass[id] ?? const <ClassMember>[];
    final assignments = _assignmentsByClass[id] ?? const <Assignment>[];
    return _copyWith(room, members: members, assignments: assignments);
  }

  @override
  Future<ClassMember> joinClass(String classId, String inviteCode) async {
    await Future<void>.delayed(delay);
    final room = _findClass(classId);
    if (room == null || room.inviteCode != inviteCode) {
      throw const ApiException('class.not_found', 'Class not found');
    }
    final members = _membersByClass[classId]!;
    final existing = members.where((m) => m.userId == 'mock-student');
    if (existing.isEmpty) {
      members.add(
        ClassMember(
          userId: 'mock-student',
          role: 'student',
          displayName: 'Student One',
          joinedAt: DateTime.now().toUtc(),
        ),
      );
    }
    return members.last;
  }

  @override
  Future<Assignment> assignLesson(
    String classId,
    String lessonRef, {
    DateTime? dueAt,
  }) async {
    await Future<void>.delayed(delay);
    final lesson = _findLesson(lessonRef);
    if (lesson == null) {
      throw const ApiException('lesson.not_found', 'Lesson not found');
    }
    final assignments = _assignmentsByClass[classId];
    if (assignments == null) {
      throw const ApiException('class.not_found', 'Class not found');
    }
    // Idempotent per (class, lesson): re-assignment returns the existing.
    for (final existing in assignments) {
      if (existing.lessonId == lesson.id) return existing;
    }
    final memberCount = (_membersByClass[classId] ?? const []).length;
    final assignment = Assignment(
      id: 'a0000000-0000-4000-8000-0000000000${_nextAssignmentId++}',
      classId: classId,
      lessonId: lesson.id,
      lessonSlug: lesson.slug,
      lessonTitle: _localized(lesson, 'en').title,
      dueAt: dueAt,
      createdAt: DateTime.now().toUtc(),
      completedCount: _completedLessons.containsKey(lesson.id) ? 1 : 0,
      memberCount: memberCount,
    );
    assignments.add(assignment);
    return assignment;
  }

  @override
  Future<List<AssignmentProgress>> fetchClassProgress(String classId) async {
    await Future<void>.delayed(delay);
    final assignments = _assignmentsByClass[classId];
    if (assignments == null) {
      throw const ApiException('class.not_found', 'Class not found');
    }
    final members = _membersByClass[classId] ?? const <ClassMember>[];
    final students = members.where((m) => !m.isTeacher).toList();
    return assignments.map((assignment) {
      return AssignmentProgress(
        assignment: assignment,
        students: students
            .map(
              (student) => StudentProgress(
                userId: student.userId,
                displayName: student.displayName,
                completed: _completedLessons.containsKey(assignment.lessonId),
                completedAt: _completedLessons[assignment.lessonId],
              ),
            )
            .toList(),
      );
    }).toList();
  }

  @override
  Future<AssignmentProgress> fetchAssignmentProgress(
    String classId,
    String assignmentId,
  ) async {
    await Future<void>.delayed(delay);
    final progresses = await fetchClassProgress(classId);
    for (final progress in progresses) {
      if (progress.assignment.id == assignmentId) return progress;
    }
    throw const ApiException('class.not_found', 'Class not found');
  }

  @override
  Future<void> deleteAssignment(String classId, String assignmentId) async {
    await Future<void>.delayed(delay);
    final assignments = _assignmentsByClass[classId];
    if (assignments == null) {
      throw const ApiException('class.not_found', 'Class not found');
    }
    assignments.removeWhere((a) => a.id == assignmentId);
  }

  @override
  Future<void> removeMember(String classId, String memberId) async {
    await Future<void>.delayed(delay);
    final members = _membersByClass[classId];
    if (members == null) {
      throw const ApiException('class.not_found', 'Class not found');
    }
    members.removeWhere((m) => m.userId == memberId);
  }

  @override
  Future<void> deleteClass(String classId) async {
    await Future<void>.delayed(delay);
    _classes.removeWhere((c) => c.id == classId);
    _membersByClass.remove(classId);
    _assignmentsByClass.remove(classId);
  }

  @override
  Future<List<Source>> searchSources(String query, {int limit = 20}) async {
    await Future<void>.delayed(delay);
    final needle = query.toLowerCase();
    final matches = _sourcesByDomain.values
        .where(
          (source) =>
              source.domain.toLowerCase().contains(needle) ||
              (source.name?.toLowerCase().contains(needle) ?? false),
        )
        .take(limit)
        .toList();
    return List.unmodifiable(matches);
  }

  @override
  Future<Source> fetchSource(String domain) async {
    await Future<void>.delayed(delay);
    final source = _sourcesByDomain[domain.toLowerCase()];
    if (source == null) {
      throw const ApiException('source.not_found', 'Source not found');
    }
    return _withCommunity(source);
  }

  @override
  Future<Source> rateSource(String domain, int rating) async {
    await Future<void>.delayed(delay);
    final source = _sourcesByDomain[domain.toLowerCase()];
    if (source == null) {
      throw const ApiException('source.not_found', 'Source not found');
    }
    // One voice per user: re-rating replaces the mock caller's rating.
    _ratingsByDomain.putIfAbsent(source.domain, () => {})['mock-user'] = rating;
    return _withCommunity(source);
  }

  // --- source internals --------------------------------------------------

  void _seedSources() {
    const seed = [
      _SeedSource('reuters.com', 'Reuters', 'news', 0.92),
      _SeedSource('apnews.com', 'AP News', 'news', 0.91),
      _SeedSource('bbc.com', 'BBC', 'news', 0.89),
      _SeedSource('theguardian.com', 'The Guardian', 'news', 0.84),
      _SeedSource('snopes.com', 'Snopes', 'fact_check', 0.95),
      _SeedSource('conspiracy-news.net', 'Conspiracy News', 'blog', 0.18),
      _SeedSource('fakeheadlines.xyz', 'Fake Headlines', 'satire', 0.05),
    ];
    for (var index = 0; index < seed.length; index++) {
      final item = seed[index];
      _sourcesByDomain[item.domain] = Source(
        id: 'src-${index + 1}',
        domain: item.domain,
        name: item.name,
        category: item.category,
        score: item.score,
        signals: const {'editorial_standards': 'high'},
        model: 'seed-v1',
        computedAt: DateTime.utc(2026, 8, 12),
      );
    }
    // A couple of pre-seeded community ratings so aggregates render.
    _ratingsByDomain['snopes.com'] = {'alice': 5, 'bob': 4};
    _ratingsByDomain['reuters.com'] = {'alice': 5};
  }

  Source _withCommunity(Source source) {
    final ratings = _ratingsByDomain[source.domain] ?? const <String, int>{};
    final count = ratings.length;
    final average = count == 0
        ? null
        : ratings.values.reduce((a, b) => a + b) / count;
    return Source(
      id: source.id,
      domain: source.domain,
      name: source.name,
      country: source.country,
      language: source.language,
      category: source.category,
      score: source.score,
      signals: source.signals,
      model: source.model,
      computedAt: source.computedAt,
      community: SourceCommunity(
        count: count,
        average: average,
        myRating: ratings['mock-user'],
      ),
    );
  }

  // --- class internals --------------------------------------------------

  static const _inviteAlphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

  static String _nextInviteCode() {
    // Deterministic per instance; the code alphabet matches the backend
    // (no confusing characters).
    final now = DateTime.now().millisecondsSinceEpoch;
    return List.generate(8, (index) {
      final shift = (now ~/ (index + 7)) % _inviteAlphabet.length;
      return _inviteAlphabet[shift];
    }).join();
  }

  ClassRoom? _findClass(String id) {
    for (final room in _classes) {
      if (room.id == id) return room;
    }
    return null;
  }

  void _seedClass() {
    final room = ClassRoom(
      id: 'c0000000-0000-4000-8000-000000000000',
      ownerId: 'mock-owner',
      name: 'Media Literacy 101',
      description: 'First period — verify before you share.',
      inviteCode: 'ANNEX234',
      role: 'teacher',
      createdAt: DateTime.utc(2026, 8, 13),
    );
    _classes.add(room);
    _membersByClass[room.id] = [
      ClassMember(
        userId: 'mock-owner',
        role: 'teacher',
        displayName: 'Ms. Alvarez',
        joinedAt: DateTime.utc(2026, 8, 13),
      ),
      ClassMember(
        userId: 'mock-student',
        role: 'student',
        displayName: 'Student One',
        joinedAt: DateTime.utc(2026, 8, 13),
      ),
    ];
    _assignmentsByClass[room.id] = [];
  }

  static ClassRoom _copyWith(
    ClassRoom room, {
    required List<ClassMember> members,
    required List<Assignment> assignments,
  }) {
    return ClassRoom(
      id: room.id,
      ownerId: room.ownerId,
      name: room.name,
      description: room.description,
      inviteCode: room.inviteCode,
      role: room.role,
      createdAt: room.createdAt,
      members: members,
      assignments: assignments,
    );
  }

  @override
  Future<List<MissingKey>> fetchMissingKeys(
    String locale, {
    String defaultLocale = 'en',
  }) async {
    await Future<void>.delayed(delay);
    // en is complete by definition; pt mirrors the seed migration's gaps
    // (en keys the pt bundle does not define yet).
    if (locale == 'pt') {
      return const [
        MissingKey(namespace: 'common', key: 'retry', englishValue: 'Retry'),
        MissingKey(
          namespace: 'lessons',
          key: 'minutes',
          englishValue: '{minutes} min',
        ),
        MissingKey(
          namespace: 'classes',
          key: 'completed_count',
          englishValue: '{completed}/{total} completed',
        ),
        MissingKey(namespace: 'settings', key: 'theme', englishValue: 'Theme'),
      ];
    }
    return const [];
  }

  @override
  Future<TranslationSuggestion> submitSuggestion({
    required String locale,
    required String namespace,
    required String key,
    required String value,
    String pluralRule = 'none',
  }) async {
    await Future<void>.delayed(delay);
    // Idempotent per (locale, key): re-submission updates the pending row.
    final existing = _mySuggestions['$locale:$key'];
    final suggestion = TranslationSuggestion(
      id:
          existing?.id ??
          's0000000-0000-4000-8000-0000000000${_nextSuggestionId++}',
      locale: locale,
      namespace: namespace,
      key: key,
      value: value,
      pluralRule: pluralRule,
      suggestedBy: 'mock-contributor',
      status: 'pending',
      createdAt: existing?.createdAt ?? DateTime.now().toUtc(),
    );
    _mySuggestions['$locale:$key'] = suggestion;
    return suggestion;
  }

  @override
  Future<List<TranslationSuggestion>> fetchMySuggestions({
    String? status,
  }) async {
    await Future<void>.delayed(delay);
    final all = _mySuggestions.values.toList()
      ..sort((a, b) => b.createdAt!.compareTo(a.createdAt!));
    if (status == null) return List.unmodifiable(all);
    return List.unmodifiable(all.where((s) => s.status == status));
  }

  @override
  Future<UserProfile> fetchMyProfile() async {
    await Future<void>.delayed(delay);
    return const UserProfile(
      id: 'mock-user',
      email: 'reader@example.com',
      displayName: 'Reader',
      role: 'moderator',
      locale: 'en',
    );
  }

  @override
  Future<List<TranslationSuggestion>> fetchPendingSuggestions({
    int limit = 50,
  }) async {
    await Future<void>.delayed(delay);
    return List.unmodifiable(
      _pendingQueue.where((s) => s.isPending).take(limit),
    );
  }

  @override
  Future<TranslationSuggestion> reviewSuggestion(
    String id,
    bool approved,
  ) async {
    await Future<void>.delayed(delay);
    final index = _pendingQueue.indexWhere((s) => s.id == id);
    if (index < 0) {
      throw const ApiException(
        'i18n.suggestion_not_found',
        'Suggestion not found',
      );
    }
    final current = _pendingQueue[index];
    final reviewed = TranslationSuggestion(
      id: current.id,
      locale: current.locale,
      namespace: current.namespace,
      key: current.key,
      value: current.value,
      pluralRule: current.pluralRule,
      suggestedBy: current.suggestedBy,
      status: approved ? 'approved' : 'rejected',
      createdAt: current.createdAt,
    );
    _pendingQueue[index] = reviewed;
    return reviewed;
  }

  // --- review queue internals --------------------------------------------

  void _seedReviewQueue() {
    if (_pendingQueue.isNotEmpty) return;
    final base = DateTime.now().toUtc();
    _pendingQueue
      ..add(
        TranslationSuggestion(
          id: 'q0000000-0000-4000-8000-000000000001',
          locale: 'es',
          namespace: 'lessons',
          key: 'complete',
          value: 'Completar',
          suggestedBy: 'contributor-1',
          createdAt: base.subtract(const Duration(days: 1)),
        ),
      )
      ..add(
        TranslationSuggestion(
          id: 'q0000000-0000-4000-8000-000000000002',
          locale: 'fr',
          namespace: 'common',
          key: 'retry',
          value: 'Réessayer',
          suggestedBy: 'contributor-2',
          createdAt: base.subtract(const Duration(hours: 3)),
        ),
      );
  }

  @override
  Future<LocaleList> fetchLocales() async {
    return const LocaleList(
      defaultLocale: 'en',
      locales: [
        LocaleInfo(code: 'en'),
        LocaleInfo(code: 'hi', fallbackCode: 'en'),
        LocaleInfo(code: 'ta', fallbackCode: 'en'),
        LocaleInfo(code: 'pt', fallbackCode: 'en'),
        LocaleInfo(code: 'es', fallbackCode: 'en'),
      ],
    );
  }

  @override
  Future<TranslationBundle> fetchBundle(String locale) async {
    // Localized lesson UI strings (mirrors the backend seed migration).
    final ownLessons = locale == 'pt'
        ? const <String, BundleEntry>{
            'lessons.title': BundleEntry(value: 'Lições', plural: 'none'),
            'lessons.complete': BundleEntry(value: 'Concluir', plural: 'none'),
            'lessons.completed': BundleEntry(
              value: 'Concluído',
              plural: 'none',
            ),
          }
        : const <String, BundleEntry>{};
    const shared = {
      'common.cancel': BundleEntry(value: 'Cancel', plural: 'none'),
      'common.retry': BundleEntry(value: 'Retry', plural: 'none'),
      'common.loading': BundleEntry(value: 'Loading…', plural: 'none'),
      'common.learn_before_you_believe': BundleEntry(
        value: 'Learn before you believe.',
        plural: 'none',
      ),
      'analysis.title': BundleEntry(value: 'Analyze', plural: 'none'),
      'analysis.submit': BundleEntry(value: 'Analyze text', plural: 'none'),
      'analysis.pending': BundleEntry(
        value: 'Analysis in progress…',
        plural: 'none',
      ),
      'analysis.processing': BundleEntry(value: 'Analyzing…', plural: 'none'),
      'analysis.failed': BundleEntry(value: 'Analysis failed', plural: 'none'),
      'analysis.summary': BundleEntry(value: 'Summary', plural: 'none'),
      'analysis.verifiability': BundleEntry(
        value: 'Verifiability',
        plural: 'none',
      ),
      'analysis.credibility_score': BundleEntry(
        value: 'Credibility score',
        plural: 'none',
      ),
      'analysis.input_hint': BundleEntry(
        value: 'Paste text to verify…',
        plural: 'none',
      ),
      'lessons.title': BundleEntry(value: 'Lessons', plural: 'none'),
      'lessons.complete': BundleEntry(value: 'Mark complete', plural: 'none'),
      'lessons.completed': BundleEntry(value: 'Completed', plural: 'none'),
      'lessons.minutes': BundleEntry(value: '{minutes} min', plural: 'other'),
      'lessons.difficulty': BundleEntry(value: 'Difficulty', plural: 'none'),
      'lessons.difficulty_beginner': BundleEntry(
        value: 'Beginner',
        plural: 'none',
      ),
      'lessons.difficulty_intermediate': BundleEntry(
        value: 'Intermediate',
        plural: 'none',
      ),
      'lessons.difficulty_advanced': BundleEntry(
        value: 'Advanced',
        plural: 'none',
      ),
      'lessons.empty': BundleEntry(
        value: 'No lessons available yet.',
        plural: 'none',
      ),
      'lessons.error': BundleEntry(
        value: 'Could not load lessons.',
        plural: 'none',
      ),
      'classes.title': BundleEntry(value: 'Classes', plural: 'none'),
      'classes.create': BundleEntry(value: 'Create class', plural: 'none'),
      'classes.join': BundleEntry(value: 'Join class', plural: 'none'),
      'classes.invite_code': BundleEntry(value: 'Invite code', plural: 'none'),
      'classes.name': BundleEntry(value: 'Class name', plural: 'none'),
      'classes.description': BundleEntry(value: 'Description', plural: 'none'),
      'classes.members': BundleEntry(value: 'Members', plural: 'none'),
      'classes.assignments': BundleEntry(value: 'Assignments', plural: 'none'),
      'classes.assign_lesson': BundleEntry(
        value: 'Assign lesson',
        plural: 'none',
      ),
      'classes.progress': BundleEntry(value: 'Progress', plural: 'none'),
      'classes.role_teacher': BundleEntry(value: 'Teacher', plural: 'none'),
      'classes.role_student': BundleEntry(value: 'Student', plural: 'none'),
      'classes.empty': BundleEntry(
        value: 'No classes yet. Create one or join with a code.',
        plural: 'none',
      ),
      'classes.error': BundleEntry(
        value: 'Could not load classes.',
        plural: 'none',
      ),
      'classes.completed_count': BundleEntry(
        value: '{completed}/{total} completed',
        plural: 'other',
      ),
      'classes.delete_class': BundleEntry(
        value: 'Delete class',
        plural: 'none',
      ),
      'classes.remove_member': BundleEntry(
        value: 'Remove member',
        plural: 'none',
      ),
      'classes.remove_assignment': BundleEntry(
        value: 'Remove assignment',
        plural: 'none',
      ),
      'classes.students': BundleEntry(value: 'Students', plural: 'none'),
      'classes.no_assignments': BundleEntry(
        value: 'No lessons assigned yet.',
        plural: 'none',
      ),
      'classes.no_members': BundleEntry(
        value: 'No students have joined yet.',
        plural: 'none',
      ),
      'classes.due': BundleEntry(value: 'Due {date}', plural: 'other'),
      'classes.class_id': BundleEntry(value: 'Class ID', plural: 'none'),
      'classes.join_hint': BundleEntry(
        value: 'Enter the class ID and invite code from your teacher.',
        plural: 'none',
      ),
      'classes.create_success': BundleEntry(
        value: 'Class created. Share the invite code with your students.',
        plural: 'none',
      ),
      'suggestions.title': BundleEntry(value: 'Contribute', plural: 'none'),
      'suggestions.missing': BundleEntry(
        value: 'Untranslated keys',
        plural: 'none',
      ),
      'suggestions.propose': BundleEntry(
        value: 'Propose translation',
        plural: 'none',
      ),
      'suggestions.your_submissions': BundleEntry(
        value: 'Your submissions',
        plural: 'none',
      ),
      'suggestions.empty': BundleEntry(
        value: 'No untranslated keys — this language is complete.',
        plural: 'none',
      ),
      'suggestions.error': BundleEntry(
        value: 'Could not load translation suggestions.',
        plural: 'none',
      ),
      'suggestions.no_submissions': BundleEntry(
        value: 'You have not submitted any translations yet.',
        plural: 'none',
      ),
      'suggestions.value': BundleEntry(
        value: 'Your translation',
        plural: 'none',
      ),
      'suggestions.english': BundleEntry(value: 'English', plural: 'none'),
      'suggestions.status_pending': BundleEntry(
        value: 'Pending review',
        plural: 'none',
      ),
      'suggestions.status_approved': BundleEntry(
        value: 'Approved',
        plural: 'none',
      ),
      'suggestions.status_rejected': BundleEntry(
        value: 'Rejected',
        plural: 'none',
      ),
      'suggestions.submitted': BundleEntry(
        value: 'Submitted for review.',
        plural: 'none',
      ),
      'suggestions.locale': BundleEntry(value: 'Language', plural: 'none'),
      'suggestions.contributor_note': BundleEntry(
        value: 'Help translate ANNEX into your language.',
        plural: 'none',
      ),
      'suggestions.review_queue': BundleEntry(
        value: 'Review queue',
        plural: 'none',
      ),
      'suggestions.approve': BundleEntry(value: 'Approve', plural: 'none'),
      'suggestions.reject': BundleEntry(value: 'Reject', plural: 'none'),
      'suggestions.no_pending': BundleEntry(
        value: 'No suggestions waiting for review.',
        plural: 'none',
      ),
      'sources.title': BundleEntry(value: 'Sources', plural: 'none'),
      'sources.search_hint': BundleEntry(
        value: 'Search publishers or domains…',
        plural: 'none',
      ),
      'sources.search': BundleEntry(value: 'Search', plural: 'none'),
      'sources.model_score': BundleEntry(value: 'Model score', plural: 'none'),
      'sources.community': BundleEntry(value: 'Community', plural: 'none'),
      'sources.rate': BundleEntry(value: 'Rate this source', plural: 'none'),
      'sources.your_rating': BundleEntry(value: 'Your rating', plural: 'none'),
      'sources.no_results': BundleEntry(
        value: 'No sources found.',
        plural: 'none',
      ),
      'sources.error': BundleEntry(
        value: 'Could not load sources.',
        plural: 'none',
      ),
      'sources.trust_signals': BundleEntry(
        value: 'Trust signals',
        plural: 'none',
      ),
      'sources.ratings_count': BundleEntry(
        value: '{count} ratings',
        plural: 'other',
      ),
      'sources.average': BundleEntry(value: '{average} avg', plural: 'other'),
      'sources.score_label': BundleEntry(
        value: 'Credibility score',
        plural: 'none',
      ),
      'sources.community_empty': BundleEntry(
        value: 'No community ratings yet.',
        plural: 'none',
      ),
      'sources.open_profile': BundleEntry(
        value: 'View profile',
        plural: 'none',
      ),
      'auth.sign_in': BundleEntry(value: 'Sign in', plural: 'none'),
      'auth.sign_out': BundleEntry(value: 'Sign out', plural: 'none'),
      'auth.continue_guest': BundleEntry(
        value: 'Continue as guest',
        plural: 'none',
      ),
      'auth.continue_google': BundleEntry(
        value: 'Continue with Google',
        plural: 'none',
      ),
      'auth.guest_label': BundleEntry(value: 'Guest', plural: 'none'),
      'settings.title': BundleEntry(value: 'Settings', plural: 'none'),
      'settings.language': BundleEntry(value: 'Language', plural: 'none'),
      'settings.theme': BundleEntry(value: 'Theme', plural: 'none'),
      'settings.theme_system': BundleEntry(value: 'System', plural: 'none'),
      'settings.theme_light': BundleEntry(value: 'Light', plural: 'none'),
      'settings.theme_dark': BundleEntry(value: 'Dark', plural: 'none'),
      'settings.account': BundleEntry(value: 'Account', plural: 'none'),
    };
    if (locale == 'en') {
      return TranslationBundle(
        locale: 'en',
        version: 1,
        entries: Map.of(shared),
      );
    }
    // Mirror the backend contract: the bundle is already resolved over the
    // fallback chain — the locale's own entries win, missing keys are
    // filled from en (ADR-0007).
    final own = locale == 'pt'
        ? const <String, BundleEntry>{
            'common.cancel': BundleEntry(value: 'Cancelar', plural: 'none'),
            'analysis.submit': BundleEntry(value: 'Analisar', plural: 'none'),
            'analysis.summary': BundleEntry(value: 'Resumo', plural: 'none'),
            'suggestions.title': BundleEntry(
              value: 'Contribuir',
              plural: 'none',
            ),
            'suggestions.missing': BundleEntry(
              value: 'Chaves não traduzidas',
              plural: 'none',
            ),
            'suggestions.propose': BundleEntry(
              value: 'Propor tradução',
              plural: 'none',
            ),
            'suggestions.your_submissions': BundleEntry(
              value: 'Suas contribuições',
              plural: 'none',
            ),
            'suggestions.status_pending': BundleEntry(
              value: 'Em análise',
              plural: 'none',
            ),
          }
        : const <String, BundleEntry>{
            'common.cancel': BundleEntry(value: 'Cancelar', plural: 'none'),
            'analysis.submit': BundleEntry(value: 'Analizar', plural: 'none'),
          };
    final merged = <String, BundleEntry>{...shared, ...ownLessons, ...own};
    return TranslationBundle(
      locale: locale,
      fallbackLocale: 'en',
      version: 1,
      entries: Map.unmodifiable(merged),
    );
  }
}

/// Localized lesson content for the mock seed (mirrors `lesson_contents`).
class _LessonContent {
  const _LessonContent({
    this.locale = 'en',
    this.title = '',
    this.summary = '',
    this.sections = const [],
  });

  final String locale;
  final String title;
  final String summary;
  final List<LessonSection> sections;
}

/// One seeded publisher (mirrors the Phase 14 source seed migration).
class _SeedSource {
  const _SeedSource(this.domain, this.name, this.category, this.score);

  final String domain;
  final String name;
  final String category;
  final double score;
}
