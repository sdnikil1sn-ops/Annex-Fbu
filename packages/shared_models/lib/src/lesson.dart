/// Education domain models (Phase 15/16).
///
/// Shapes mirror the backend lessons contract: `GET /lessons` returns the
/// localized list with per-user progress, `GET /lessons/{id or slug}`
/// adds the resolved `locale` and content `sections`, and
/// `POST /lessons/{id or slug}/complete` returns `lesson_id` +
/// `completed_at`.
library;

/// One content section within a localized lesson.
class LessonSection {
  const LessonSection(
      {required this.heading, required this.body, this.bullets = const []});

  final String heading;
  final String body;

  /// Optional bullet points rendered under the body text.
  final List<String> bullets;

  factory LessonSection.fromJson(Map<String, dynamic> json) {
    final heading = json['heading'];
    final body = json['body'];
    if (heading is! String || heading.isEmpty) {
      throw const FormatException('Lesson section requires a heading');
    }
    if (body is! String) {
      throw const FormatException('Lesson section requires a body');
    }
    final bullets = json['bullets'];
    return LessonSection(
      heading: heading,
      body: body,
      bullets: bullets is List
          ? bullets.map((item) => item.toString()).toList()
          : const [],
    );
  }

  Map<String, dynamic> toJson() =>
      {'heading': heading, 'body': body, 'bullets': bullets};
}

/// A lesson as returned by the API.
///
/// The list endpoint returns metadata + progress; the detail endpoint
/// additionally carries the resolved `locale` and `sections`.
class Lesson {
  const Lesson({
    required this.id,
    required this.slug,
    this.difficulty = 'beginner',
    this.category = 'media_literacy',
    this.estimatedMinutes = 5,
    this.orderIndex = 0,
    this.title,
    this.summary,
    this.completed = false,
    this.completedAt,
    this.locale,
    this.sections = const [],
  });

  final String id;
  final String slug;

  /// `beginner` | `intermediate` | `advanced`.
  final String difficulty;

  /// Curriculum category (e.g. `media_literacy`).
  final String category;

  /// Reading time estimate in minutes.
  final int estimatedMinutes;

  /// Curriculum ordering.
  final int orderIndex;

  /// Localized title (null when the lesson has no content in any
  /// fallback-chain locale).
  final String? title;

  /// Localized summary.
  final String? summary;

  /// Whether the requesting user has completed this lesson.
  final bool completed;

  /// When the user completed it, if completed.
  final DateTime? completedAt;

  /// The locale the content was resolved in (detail payload only).
  final String? locale;

  /// Content sections (detail payload only).
  final List<LessonSection> sections;

  factory Lesson.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final slug = json['slug'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('Lesson requires an id');
    }
    if (slug is! String || slug.isEmpty) {
      throw const FormatException('Lesson requires a slug');
    }
    final sections = json['sections'];
    final completedAt = json['completed_at'];
    return Lesson(
      id: id,
      slug: slug,
      difficulty: json['difficulty'] as String? ?? 'beginner',
      category: json['category'] as String? ?? 'media_literacy',
      estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ?? 5,
      orderIndex: (json['order_index'] as num?)?.toInt() ?? 0,
      title: json['title'] as String?,
      summary: json['summary'] as String?,
      completed: json['completed'] as bool? ?? false,
      completedAt:
          completedAt == null ? null : DateTime.parse(completedAt as String),
      locale: json['locale'] as String?,
      sections: sections is List
          ? sections
              .map((item) => LessonSection.fromJson(
                  Map<String, dynamic>.from(item as Map)))
              .toList()
          : const [],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'slug': slug,
        'difficulty': difficulty,
        'category': category,
        'estimated_minutes': estimatedMinutes,
        'order_index': orderIndex,
        'title': title,
        'summary': summary,
        'completed': completed,
        'completed_at': completedAt?.toIso8601String(),
        'locale': locale,
        'sections': sections.map((section) => section.toJson()).toList(),
      };
}

/// The result of completing a lesson.
class LessonProgress {
  const LessonProgress({required this.lessonId, required this.completedAt});

  final String lessonId;
  final DateTime completedAt;

  factory LessonProgress.fromJson(Map<String, dynamic> json) {
    final lessonId = json['lesson_id'];
    final completedAt = json['completed_at'];
    if (lessonId is! String || lessonId.isEmpty) {
      throw const FormatException('LessonProgress requires a lesson_id');
    }
    if (completedAt is! String) {
      throw const FormatException('LessonProgress requires a completed_at');
    }
    return LessonProgress(
      lessonId: lessonId,
      completedAt: DateTime.parse(completedAt),
    );
  }

  Map<String, dynamic> toJson() => {
        'lesson_id': lessonId,
        'completed_at': completedAt.toIso8601String(),
      };
}
