import 'package:flutter_test/flutter_test.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_models/shared_models.dart';

void main() {
  test('search finds sources by domain substring', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);

    await controller.search('reuters');

    expect(controller.state, SourcesFlowState.loaded);
    expect(controller.query, 'reuters');
    expect(controller.results, hasLength(1));
    expect(controller.results.first.domain, 'reuters.com');
    expect(controller.results.first.score, 0.92);
  });

  test('search finds sources by name substring (case-insensitive)', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);

    await controller.search('SNOPES');

    expect(controller.results, hasLength(1));
    expect(controller.results.first.name, 'Snopes');
  });

  test('search with no matches returns an empty list', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);

    await controller.search('zzz-not-a-source');

    expect(controller.state, SourcesFlowState.loaded);
    expect(controller.results, isEmpty);
  });

  test('open loads the profile with the community aggregate', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);
    await controller.search('snopes');

    await controller.open('snopes.com');

    final source = controller.selected;
    expect(source, isNotNull);
    expect(source!.name, 'Snopes');
    expect(source.score, 0.95);
    // Pre-seeded community ratings: two voices with a 4.5 average.
    expect(source.community.count, 2);
    expect(source.community.average, 4.5);
    expect(source.community.hasRated, isFalse);
  });

  test('open failure records an error and keeps the results', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);
    await controller.search('snopes');

    await controller.open('unknown-domain.com');

    expect(controller.error, isNotNull);
    expect(controller.selected, isNull);
    expect(controller.results, isNotEmpty);
  });

  test('rate records one voice per user and updates the aggregate', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);
    await controller.open('snopes.com');

    final ok = await controller.rate(3);

    expect(ok, isTrue);
    expect(controller.error, isNull);
    final source = controller.selected!;
    expect(source.community.count, 3); // two seeded + the caller
    expect(source.community.hasRated, isTrue);
    expect(source.community.myRating, 3);
    expect(source.community.average, (5 + 4 + 3) / 3);
  });

  test('re-rating replaces the caller rating (one voice)', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);
    await controller.open('reuters.com');

    await controller.rate(2);
    await controller.rate(5);

    final source = controller.selected!;
    expect(source.community.count, 2); // one seeded + the caller
    expect(source.community.myRating, 5);
    expect(source.community.average, (5 + 5) / 2);
  });

  test('rate on a profile with no ratings reports the empty state', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);
    await controller.open('bbc.com');

    final source = controller.selected!;
    expect(source.community.count, 0);
    expect(source.community.average, isNull);
    expect(source.community.hasRated, isFalse);
  });

  test('search failure transitions to failed state', () async {
    final api = _ThrowingApi();
    final controller = SourcesController(api: api);

    await controller.search('reuters');

    expect(controller.state, SourcesFlowState.failed);
    expect(controller.error, isNotNull);
  });

  test('closeProfile clears the selection', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SourcesController(api: api);
    await controller.open('snopes.com');

    controller.closeProfile();

    expect(controller.selected, isNull);
  });
}

/// An API whose sources endpoints always fail.
class _ThrowingApi extends MockAnalysisApi {
  @override
  Future<List<Source>> searchSources(String query, {int limit = 20}) async {
    throw const ApiException('sources.error', 'boom');
  }
}
