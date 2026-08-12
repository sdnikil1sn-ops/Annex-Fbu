import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('Lesson', () {
    test('round-trips the list payload from the API', () {
      const wire = {
        'id': 'f0f0f0f0-0000-4000-8000-000000000001',
        'slug': 'spotting-misinformation',
        'difficulty': 'beginner',
        'category': 'media_literacy',
        'estimated_minutes': 5,
        'order_index': 1,
        'title': 'Spotting Misinformation',
        'summary': 'Learn to recognize the common patterns.',
        'completed': false,
        'completed_at': null,
      };

      final lesson = Lesson.fromJson(wire);
      expect(lesson.id, 'f0f0f0f0-0000-4000-8000-000000000001');
      expect(lesson.slug, 'spotting-misinformation');
      expect(lesson.difficulty, 'beginner');
      expect(lesson.estimatedMinutes, 5);
      expect(lesson.orderIndex, 1);
      expect(lesson.title, 'Spotting Misinformation');
      expect(lesson.completed, isFalse);
      expect(lesson.completedAt, isNull);
      expect(lesson.locale, isNull);
      expect(lesson.sections, isEmpty);

      final decoded = Lesson.fromJson(lesson.toJson());
      expect(decoded.slug, lesson.slug);
      expect(decoded.title, lesson.title);
      expect(decoded.toJson()['completed'], lesson.toJson()['completed']);
    });

    test('round-trips the detail payload with sections and progress', () {
      final lesson = Lesson.fromJson(const {
        'id': 'f0f0f0f0-0000-4000-8000-000000000002',
        'slug': 'verifying-images',
        'difficulty': 'intermediate',
        'category': 'media_literacy',
        'estimated_minutes': 8,
        'order_index': 2,
        'title': 'Verifying Images',
        'summary': 'Use OCR and forensics.',
        'completed': true,
        'completed_at': '2026-08-12T10:00:00Z',
        'locale': 'en',
        'sections': [
          {
            'heading': 'Why images need verification',
            'body': 'Images are easy to take out of context.',
            'bullets': ['Read the text with OCR', 'Check forensics signals'],
          },
        ],
      });

      expect(lesson.completed, isTrue);
      expect(lesson.completedAt, DateTime.parse('2026-08-12T10:00:00Z'));
      expect(lesson.locale, 'en');
      expect(lesson.sections, hasLength(1));
      expect(lesson.sections.first.heading, 'Why images need verification');
      expect(lesson.sections.first.bullets, hasLength(2));

      final decoded = Lesson.fromJson(lesson.toJson());
      expect(decoded.locale, lesson.locale);
      expect(decoded.sections.first.body, lesson.sections.first.body);
      expect(decoded.toJson(), lesson.toJson());
    });

    test('rejects a lesson without an id or slug', () {
      expect(() => Lesson.fromJson(const {'slug': 'x'}), throwsFormatException);
      expect(() => Lesson.fromJson(const {'id': 'x'}), throwsFormatException);
    });
  });

  group('LessonSection', () {
    test('bullets default to empty when absent', () {
      final section = LessonSection.fromJson(const {
        'heading': 'h',
        'body': 'b',
      });
      expect(section.bullets, isEmpty);
    });

    test('rejects a section without a heading', () {
      expect(
        () => LessonSection.fromJson(const {'body': 'b'}),
        throwsFormatException,
      );
    });
  });

  group('LessonProgress', () {
    test('round-trips the completion payload', () {
      const wire = {
        'lesson_id': 'f0f0f0f0-0000-4000-8000-000000000001',
        'completed_at': '2026-08-12T10:00:00Z',
      };
      final progress = LessonProgress.fromJson(wire);
      expect(progress.lessonId, wire['lesson_id']);
      expect(progress.completedAt, DateTime.parse('2026-08-12T10:00:00Z'));

      final decoded = LessonProgress.fromJson(progress.toJson());
      expect(decoded.lessonId, progress.lessonId);
      expect(decoded.completedAt, progress.completedAt);
    });

    test('rejects a completion without lesson_id', () {
      expect(
        () => LessonProgress.fromJson(const {'completed_at': 'x'}),
        throwsFormatException,
      );
    });
  });
}
