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
  });

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

  /// Whether the last submission was recorded (test hook).
  String? lastSubmittedText;
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
            report: initialReport ?? _report,
            createdAt: current.createdAt,
            completedAt: DateTime.now().toUtc(),
          );
    _analyses[index] = updated;
    return updated;
  }

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

  static final List<Lesson> _seed = [
    const Lesson(
      id: '00000000-0000-4000-8000-000000000001',
      slug: 'spotting-misinformation',
      difficulty: 'beginner',
      category: 'media_literacy',
      estimatedMinutes: 5,
      orderIndex: 1,
    ),
    const Lesson(
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
  Future<LocaleList> fetchLocales() async {
    return const LocaleList(
      defaultLocale: 'en',
      locales: [
        LocaleInfo(code: 'en'),
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
