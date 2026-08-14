import 'package:flutter_test/flutter_test.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_models/shared_models.dart';

void main() {
  test('load fetches missing keys and submissions for the locale', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SuggestionsController(api: api);

    expect(controller.state, SuggestionsFlowState.idle);
    await controller.load('pt');

    expect(controller.state, SuggestionsFlowState.loaded);
    expect(controller.missing, hasLength(4));
    expect(controller.missing.first.fullKey, 'common.retry');
    expect(controller.missing.first.englishValue, 'Retry');
    expect(controller.submissions, isEmpty);
  });

  test('en has no missing keys (the default locale is complete)', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SuggestionsController(api: api);

    await controller.load('en');

    expect(controller.missing, isEmpty);
    expect(controller.submissions, isEmpty);
  });

  test(
    'submit proposes a translation and removes the key from missing',
    () async {
      final api = MockAnalysisApi(delay: Duration.zero);
      final controller = SuggestionsController(api: api);
      await controller.load('pt');
      final key = controller.missing.first; // common.retry

      final ok = await controller.submit(
        locale: 'pt',
        key: key,
        value: 'Tentar novamente',
      );

      expect(ok, isTrue);
      expect(controller.error, isNull);
      // The proposed key stops being missing and shows as pending.
      expect(
        controller.missing.any((item) => item.fullKey == 'common.retry'),
        isFalse,
      );
      expect(controller.missing, hasLength(3));
      expect(controller.submissions, hasLength(1));
      expect(controller.submissions.first.fullKey, 'common.retry');
      expect(controller.submissions.first.value, 'Tentar novamente');
      expect(controller.submissions.first.isPending, isTrue);
    },
  );

  test('re-submitting the same key updates the existing submission', () async {
    final api = MockAnalysisApi(delay: Duration.zero);
    final controller = SuggestionsController(api: api);
    await controller.load('pt');
    final key = controller.missing.first;

    await controller.submit(locale: 'pt', key: key, value: 'Tentar novamente');
    await controller.submit(locale: 'pt', key: key, value: 'Tente de novo');

    expect(controller.submissions, hasLength(1));
    expect(controller.submissions.first.value, 'Tente de novo');
  });

  test('load failure transitions to failed state', () async {
    final api = _ThrowingApi();
    final controller = SuggestionsController(api: api);

    await controller.load('pt');

    expect(controller.state, SuggestionsFlowState.failed);
    expect(controller.error, isNotNull);
  });

  test('submit failure records an error and keeps the list', () async {
    final api = _ThrowingSubmitApi();
    final controller = SuggestionsController(api: api);
    await controller.load('pt');
    final key = controller.missing.first;

    final ok = await controller.submit(locale: 'pt', key: key, value: 'x');

    expect(ok, isFalse);
    expect(controller.error, isNotNull);
    expect(controller.submissions, isEmpty);
  });
}

/// An API whose missing-keys endpoint always fails.
class _ThrowingApi extends MockAnalysisApi {
  @override
  Future<List<MissingKey>> fetchMissingKeys(
    String locale, {
    String defaultLocale = 'en',
  }) async {
    throw const ApiException('i18n.error', 'boom');
  }
}

/// An API whose submit endpoint always fails.
class _ThrowingSubmitApi extends MockAnalysisApi {
  @override
  Future<TranslationSuggestion> submitSuggestion({
    required String locale,
    required String namespace,
    required String key,
    required String value,
    String pluralRule = 'none',
  }) async {
    throw const ApiException('i18n.error', 'boom');
  }
}
