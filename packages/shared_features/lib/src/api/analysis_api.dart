/// Backend API abstraction for the analysis and i18n endpoints.
///
/// The app depends on [AnalysisApi]; production uses [HttpAnalysisApi],
/// tests use the explicit mock (CONTRIBUTING: mocks never ship in prod
/// paths and are named `Mock*`).
library;

import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_models/shared_models.dart';

/// Thrown when the backend answers outside the expected envelope.
class ApiException implements Exception {
  const ApiException(this.code, this.message);

  /// Machine-readable error code from the envelope (e.g. `analysis.not_found`).
  final String code;
  final String message;

  @override
  String toString() => 'ApiException($code): $message';
}

/// The backend surface the app consumes.
abstract interface class AnalysisApi {
  /// Submit text for analysis; returns the created (pending) analysis.
  Future<Analysis> submitText(String text, {String locale = 'en'});

  /// Submit an image (base64 or ``data:`` URL) for OCR + forensics-based
  /// claim analysis; returns the created (pending) analysis.
  Future<Analysis> submitImage(String image, {String locale = 'en'});

  /// Fetch an analysis by id (polling).
  Future<Analysis> fetchAnalysis(String id);

  /// The enabled locales with their fallback parents.
  Future<LocaleList> fetchLocales();

  /// A resolved translation bundle for a locale.
  Future<TranslationBundle> fetchBundle(String locale);

  /// The published curriculum, localized for [locale], with per-user
  /// completion progress.
  Future<List<Lesson>> fetchLessons({String locale = 'en'});

  /// One lesson by UUID or stable slug, with localized content and
  /// sections (Phase 15).
  Future<Lesson> fetchLesson(String idOrSlug, {String locale = 'en'});

  /// Mark a lesson complete (idempotent; the first completion wins).
  Future<LessonProgress> completeLesson(String idOrSlug);

  /// Create a class; the caller becomes its teacher.
  Future<ClassRoom> createClass(String name, String description);

  /// The caller's classes (owned or joined) with their membership role.
  Future<List<ClassRoom>> fetchClasses();

  /// One class with its member roster and assignments (members only).
  Future<ClassRoom> fetchClass(String id);

  /// Join a class by its invite code (idempotent).
  Future<ClassMember> joinClass(String classId, String inviteCode);

  /// Assign a published lesson to a class (teacher only, idempotent).
  Future<Assignment> assignLesson(
    String classId,
    String lessonRef, {
    DateTime? dueAt,
  });

  /// Per-assignment, per-student completion for a class (teacher only).
  Future<List<AssignmentProgress>> fetchClassProgress(String classId);

  /// Per-student completion for one assignment (teacher only).
  Future<AssignmentProgress> fetchAssignmentProgress(
    String classId,
    String assignmentId,
  );

  /// Remove an assignment (teacher only).
  Future<void> deleteAssignment(String classId, String assignmentId);

  /// Remove a member from a class (teacher only).
  Future<void> removeMember(String classId, String memberId);

  /// Delete a class and its members/assignments (owner only).
  Future<void> deleteClass(String classId);

  /// Keys the default locale defines that [locale] has not translated
  /// (public, like the bundle endpoints).
  Future<List<MissingKey>> fetchMissingKeys(
    String locale, {
    String defaultLocale = 'en',
  });

  /// Submit a translation proposal for an enabled locale; the caller
  /// becomes its author and the suggestion starts pending.
  Future<TranslationSuggestion> submitSuggestion({
    required String locale,
    required String namespace,
    required String key,
    required String value,
    String pluralRule = 'none',
  });

  /// The caller's submissions, newest first (optional status filter).
  Future<List<TranslationSuggestion>> fetchMySuggestions({String? status});

  /// Search sources by domain or name (case-insensitive substring).
  Future<List<Source>> searchSources(String query, {int limit = 20});

  /// One source profile with its credibility score and the community
  /// aggregate (public; carries the caller's rating when authenticated).
  Future<Source> fetchSource(String domain);

  /// Rate a source's credibility (1–5), updating the community signal;
  /// re-rating replaces the caller's own rating (one voice per user).
  Future<Source> rateSource(String domain, int rating);

  /// The authenticated caller's hydrated profile (role, locale).
  Future<UserProfile> fetchMyProfile();

  /// The moderator review queue, oldest first (moderator/admin only).
  Future<List<TranslationSuggestion>> fetchPendingSuggestions({int limit = 50});

  /// Approve or reject a pending suggestion (moderator/admin only);
  /// approval publishes the value into the live bundles.
  Future<TranslationSuggestion> reviewSuggestion(String id, bool approved);
}

/// HTTP implementation against the v1 backend API.
class HttpAnalysisApi implements AnalysisApi {
  HttpAnalysisApi({
    required this.baseUrl,
    http.Client? client,
    this.tokenProvider,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  /// Supplies the Firebase ID token for the Authorization header, or null
  /// for anonymous requests.
  final Future<String?> Function()? tokenProvider;

  @override
  Future<Analysis> submitText(String text, {String locale = 'en'}) async {
    final json = await _post('/analysis', {
      'input_type': 'text',
      'text': text,
      'locale': locale,
    });
    return _analysisFromJson(json);
  }

  @override
  Future<Analysis> submitImage(String image, {String locale = 'en'}) async {
    final json = await _post('/analysis', {
      'input_type': 'image',
      'image': image,
      'locale': locale,
    });
    return _analysisFromJson(json);
  }

  Analysis _analysisFromJson(Map<String, dynamic> json) {
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'analysis.invalid_response',
        'Malformed analysis response',
      );
    }
    return Analysis.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<Analysis> fetchAnalysis(String id) async {
    final json = await _get('/analysis/$id');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'analysis.invalid_response',
        'Malformed analysis response',
      );
    }
    return Analysis.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<LocaleList> fetchLocales() async {
    final json = await _get('/i18n/locales');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed locales response',
      );
    }
    return LocaleList.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<TranslationBundle> fetchBundle(String locale) async {
    final json = await _get('/i18n/bundles/$locale');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed bundle response',
      );
    }
    return TranslationBundle.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<List<Lesson>> fetchLessons({String locale = 'en'}) async {
    final json = await _get('/lessons?locale=$locale');
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'lessons.invalid_response',
        'Malformed lessons response',
      );
    }
    return data
        .map((item) => Lesson.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  @override
  Future<Lesson> fetchLesson(String idOrSlug, {String locale = 'en'}) async {
    final json = await _get('/lessons/$idOrSlug?locale=$locale');
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'lessons.invalid_response',
        'Malformed lesson response',
      );
    }
    return Lesson.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<LessonProgress> completeLesson(String idOrSlug) async {
    final json = await _post('/lessons/$idOrSlug/complete', const {});
    final data = json['data'];
    if (data is! Map) {
      throw const ApiException(
        'lessons.invalid_response',
        'Malformed completion response',
      );
    }
    return LessonProgress.fromJson(Map<String, dynamic>.from(data));
  }

  @override
  Future<ClassRoom> createClass(String name, String description) async {
    final json = await _post('/classes', {
      'name': name,
      'description': description,
    });
    return ClassRoom.fromJson(_dataMap(json, 'classes'));
  }

  @override
  Future<List<ClassRoom>> fetchClasses() async {
    final json = await _get('/classes');
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'classes.invalid_response',
        'Malformed classes response',
      );
    }
    return data
        .map(
          (item) => ClassRoom.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList();
  }

  @override
  Future<ClassRoom> fetchClass(String id) async {
    final json = await _get('/classes/$id');
    return ClassRoom.fromJson(_dataMap(json, 'classes'));
  }

  @override
  Future<ClassMember> joinClass(String classId, String inviteCode) async {
    final json = await _post('/classes/$classId/join', {
      'invite_code': inviteCode,
    });
    return ClassMember.fromJson(_dataMap(json, 'classes'));
  }

  @override
  Future<Assignment> assignLesson(
    String classId,
    String lessonRef, {
    DateTime? dueAt,
  }) async {
    final json = await _post('/classes/$classId/assignments', {
      'lesson_ref': lessonRef,
      if (dueAt != null) 'due_at': dueAt.toIso8601String(),
    });
    return Assignment.fromJson(_dataMap(json, 'classes'));
  }

  @override
  Future<List<AssignmentProgress>> fetchClassProgress(String classId) async {
    final json = await _get('/classes/$classId/progress');
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'classes.invalid_response',
        'Malformed progress response',
      );
    }
    return data
        .map(
          (item) => AssignmentProgress.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .toList();
  }

  @override
  Future<AssignmentProgress> fetchAssignmentProgress(
    String classId,
    String assignmentId,
  ) async {
    final json = await _get(
      '/classes/$classId/assignments/$assignmentId/progress',
    );
    return AssignmentProgress.fromJson(_dataMap(json, 'classes'));
  }

  @override
  Future<void> deleteAssignment(String classId, String assignmentId) async {
    await _delete('/classes/$classId/assignments/$assignmentId');
  }

  @override
  Future<void> removeMember(String classId, String memberId) async {
    await _delete('/classes/$classId/members/$memberId');
  }

  @override
  Future<void> deleteClass(String classId) async {
    await _delete('/classes/$classId');
  }

  @override
  Future<List<MissingKey>> fetchMissingKeys(
    String locale, {
    String defaultLocale = 'en',
  }) async {
    final json = await _get(
      '/i18n/suggestions/missing?locale=$locale&default_locale=$defaultLocale',
    );
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed missing-keys response',
      );
    }
    return data
        .map(
          (item) => MissingKey.fromJson(Map<String, dynamic>.from(item as Map)),
        )
        .toList();
  }

  @override
  Future<TranslationSuggestion> submitSuggestion({
    required String locale,
    required String namespace,
    required String key,
    required String value,
    String pluralRule = 'none',
  }) async {
    final json = await _post('/i18n/suggestions', {
      'locale': locale,
      'namespace': namespace,
      'key': key,
      'value': value,
      'plural_rule': pluralRule,
    });
    return TranslationSuggestion.fromJson(_dataMap(json, 'i18n'));
  }

  @override
  Future<List<TranslationSuggestion>> fetchMySuggestions({
    String? status,
  }) async {
    final query = status == null ? '' : '?status=$status';
    final json = await _get('/i18n/suggestions$query');
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed suggestions response',
      );
    }
    return data
        .map(
          (item) => TranslationSuggestion.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .toList();
  }

  @override
  Future<List<Source>> searchSources(String query, {int limit = 20}) async {
    final encoded = Uri.encodeQueryComponent(query);
    final json = await _get('/sources/search?q=$encoded&limit=$limit');
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'sources.invalid_response',
        'Malformed sources response',
      );
    }
    return data
        .map((item) => Source.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList();
  }

  @override
  Future<Source> fetchSource(String domain) async {
    final json = await _get('/sources/${Uri.encodeComponent(domain)}');
    return Source.fromJson(_dataMap(json, 'sources'));
  }

  @override
  Future<Source> rateSource(String domain, int rating) async {
    final json = await _post('/sources/${Uri.encodeComponent(domain)}/rate', {
      'rating': rating,
    });
    return Source.fromJson(_dataMap(json, 'sources'));
  }

  @override
  Future<UserProfile> fetchMyProfile() async {
    final json = await _get('/users/me');
    return UserProfile.fromJson(_dataMap(json, 'users'));
  }

  @override
  Future<List<TranslationSuggestion>> fetchPendingSuggestions({
    int limit = 50,
  }) async {
    final json = await _get('/i18n/suggestions/pending?limit=$limit');
    final data = json['data'];
    if (data is! List) {
      throw const ApiException(
        'i18n.invalid_response',
        'Malformed pending suggestions response',
      );
    }
    return data
        .map(
          (item) => TranslationSuggestion.fromJson(
            Map<String, dynamic>.from(item as Map),
          ),
        )
        .toList();
  }

  @override
  Future<TranslationSuggestion> reviewSuggestion(
    String id,
    bool approved,
  ) async {
    final json = await _post('/i18n/suggestions/$id/review', {
      'approved': approved,
    });
    return TranslationSuggestion.fromJson(_dataMap(json, 'i18n'));
  }

  Map<String, dynamic> _dataMap(Map<String, dynamic> json, String prefix) {
    final data = json['data'];
    if (data is! Map) {
      throw ApiException(
        '$prefix.invalid_response',
        'Malformed $prefix response',
      );
    }
    return Map<String, dynamic>.from(data);
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _client.get(
      _uri(path),
      headers: await _headers(),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _client.post(
      _uri(path),
      headers: {...await _headers(), 'content-type': 'application/json'},
      body: jsonEncode(body),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> _delete(String path) async {
    final response = await _client.delete(
      _uri(path),
      headers: await _headers(),
    );
    return _decode(response);
  }

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, String>> _headers() async {
    final token = await tokenProvider?.call();
    return {
      if (token != null && token.isNotEmpty) 'authorization': 'Bearer $token',
      'accept': 'application/json',
    };
  }

  Map<String, dynamic> _decode(http.Response response) {
    Map<String, dynamic> body;
    try {
      body =
          jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      throw ApiException('api.invalid_response', 'Response was not valid JSON');
    }
    if (response.statusCode >= 400) {
      final error = body['error'];
      if (error is Map) {
        throw ApiException(
          error['code'] as String? ?? 'api.error',
          error['message'] as String? ?? 'Request failed',
        );
      }
      throw ApiException(
        'api.error',
        'Request failed (${response.statusCode})',
      );
    }
    return body;
  }
}
