import 'package:flutter_test/flutter_test.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_models/shared_models.dart';

void main() {
  test('loads the English bundle and resolves typed keys', () async {
    final controller = I18nController(api: MockAnalysisApi(), locale: 'en');
    addTearDown(controller.dispose);

    await controller.load();

    expect(controller.locale, 'en');
    expect(controller.loading, isFalse);
    expect(controller.t('analysis.submit'), 'Analyze text');
    expect(controller.t('common.cancel'), 'Cancel');
    expect(controller.locales, isNotNull);
  });

  test('loads other locales with the fallback chain', () async {
    final controller = I18nController(api: MockAnalysisApi(), locale: 'pt');
    addTearDown(controller.dispose);

    await controller.load();

    // pt bundle defines its own value for analysis.submit.
    expect(controller.t('analysis.submit'), 'Analisar');
    // Keys absent from the pt bundle resolve to the fallback en value
    // (the mock merges the fallback chain like the backend).
    expect(controller.t('analysis.title'), 'Analyze');
    expect(controller.t('settings.title'), 'Settings');
  });

  test('fallbackChain resolves requested → parent → default', () async {
    final controller = I18nController(api: MockAnalysisApi(), locale: 'pt');
    addTearDown(controller.dispose);

    await controller.load();

    final chain = controller.fallbackChain();
    expect(chain.first, 'pt');
    expect(chain.last, 'en');
    expect(chain, contains('en'));
  });

  test('unknown keys fall back to the key itself', () async {
    final controller = I18nController(api: MockAnalysisApi(), locale: 'en');
    addTearDown(controller.dispose);

    await controller.load();

    expect(controller.t('no.such.key'), 'no.such.key');
  });

  test('load failure records an error', () async {
    final controller = I18nController(api: _FailingApi(), locale: 'en');
    addTearDown(controller.dispose);

    await controller.load();

    expect(controller.error, isNotNull);
    // Keys still resolve to themselves when no bundle is available.
    expect(controller.t('analysis.submit'), 'analysis.submit');
  });
}

/// An API whose i18n endpoints fail.
class _FailingApi extends MockAnalysisApi {
  @override
  Future<TranslationBundle> fetchBundle(String locale) async {
    throw ApiException('i18n.locale_not_found', 'Locale is not available');
  }
}
