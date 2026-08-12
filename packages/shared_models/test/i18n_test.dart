import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('LocaleList', () {
    test('round-trips the locales endpoint payload', () {
      const wire = {
        'default_locale': 'en',
        'locales': [
          {'code': 'en', 'fallback_code': null},
          {'code': 'pt', 'fallback_code': 'en'},
        ],
      };
      final list = LocaleList.fromJson(wire);
      expect(list.defaultLocale, 'en');
      expect(list.locales, hasLength(2));
      expect(list.locales[1].fallbackCode, 'en');

      final decoded = LocaleList.fromJson(list.toJson());
      expect(decoded.defaultLocale, 'en');
      expect(decoded.locales[1].code, 'pt');
    });
  });

  group('TranslationBundle', () {
    test('round-trips a resolved bundle', () {
      final bundle = TranslationBundle.fromJson(const {
        'locale': 'pt',
        'fallback_locale': 'en',
        'version': 3,
        'entries': {
          'common.cancel': {'value': 'Cancelar', 'plural': 'none'},
          'common.claims_count': {
            'value': '{count} alegações',
            'plural': 'other'
          },
        },
      });

      expect(bundle['common.cancel']!.value, 'Cancelar');
      expect(bundle['common.claims_count']!.plural, 'other');
      expect(bundle['missing.key'], isNull);

      final decoded = TranslationBundle.fromJson(bundle.toJson());
      expect(decoded.version, 3);
      expect(decoded['common.cancel']!.value, 'Cancelar');
    });

    test('entries default plural to none', () {
      final bundle = TranslationBundle.fromJson(const {
        'locale': 'en',
        'version': 1,
        'entries': {
          'common.save': {'value': 'Save'}
        },
      });
      expect(bundle['common.save']!.plural, 'none');
    });

    test('rejects a bundle without entries', () {
      expect(
        () => TranslationBundle.fromJson(const {'locale': 'en', 'version': 1}),
        throwsFormatException,
      );
    });
  });
}
