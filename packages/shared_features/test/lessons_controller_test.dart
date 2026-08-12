import 'package:flutter_test/flutter_test.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_models/shared_models.dart';

void main() {
  test('load fetches the localized curriculum in order', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = LessonsController(api: api);

    expect(controller.state, LessonsFlowState.idle);
    await controller.load('en');

    expect(controller.state, LessonsFlowState.loaded);
    expect(controller.lessons, hasLength(2));
    expect(controller.lessons.first.slug, 'spotting-misinformation');
    expect(controller.lessons.first.title, 'Spotting Misinformation');
    expect(controller.lessons.first.completed, isFalse);
    expect(controller.lessons[1].slug, 'understanding-credibility-scores');
  });

  test('load resolves the localized content per locale', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = LessonsController(api: api);

    await controller.load('pt');

    expect(controller.lessons.first.title, 'Como Detectar Desinformação');
    // The second lesson has no pt variant -> falls back to en.
    expect(controller.lessons[1].title, 'Understanding Credibility Scores');
  });

  test('open loads the lesson detail with sections', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = LessonsController(api: api);

    await controller.open('spotting-misinformation', locale: 'en');

    final lesson = controller.selected;
    expect(lesson, isNotNull);
    expect(lesson!.sections, isNotEmpty);
    expect(lesson.sections.first.heading, 'Why misinformation spreads');
    expect(lesson.sections.first.bullets, isNotEmpty);
    expect(lesson.locale, 'en');
  });

  test('complete marks the lesson and keeps the list in sync', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = LessonsController(api: api);
    await controller.load('en');

    await controller.open(controller.lessons.first.id, locale: 'en');
    await controller.complete(locale: 'en');

    expect(controller.selected!.completed, isTrue);
    expect(controller.selected!.completedAt, isNotNull);
    // The list reflects the completion for the back-navigation checkmark.
    expect(controller.lessons.first.completed, isTrue);
    expect(controller.lessons[1].completed, isFalse);
  });

  test('open failure records an error and keeps the list', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = LessonsController(api: api);
    await controller.load('en');

    await controller.open('no-such-lesson', locale: 'en');

    expect(controller.error, isNotNull);
    expect(controller.selected, isNull);
    expect(controller.lessons, hasLength(2));
  });

  test('load failure transitions to failed state', () async {
    final api = _ThrowingApi();
    final controller = LessonsController(api: api);

    await controller.load('en');

    expect(controller.state, LessonsFlowState.failed);
    expect(controller.error, isNotNull);
  });

  test('closeDetail clears the selection', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = LessonsController(api: api);
    await controller.open('spotting-misinformation', locale: 'en');

    controller.closeDetail();

    expect(controller.selected, isNull);
  });
}

/// An API whose lessons endpoints always fail.
class _ThrowingApi extends MockAnalysisApi {
  @override
  Future<List<Lesson>> fetchLessons({String locale = 'en'}) async {
    throw const ApiException('lessons.error', 'boom');
  }
}
