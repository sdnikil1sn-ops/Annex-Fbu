import 'package:shared_utils/shared_utils.dart';
import 'package:test/test.dart';

void main() {
  const locales = <String, LocaleNode>{
    'en': LocaleNode('en'),
    'pt': LocaleNode('pt', fallbackCode: 'en'),
    'pt-BR': LocaleNode('pt-BR', fallbackCode: 'pt'),
    'es': LocaleNode('es', fallbackCode: 'en'),
    'ar': LocaleNode('ar', fallbackCode: 'en'),
  };

  group('resolveFallbackChain', () {
    test('default locale resolves to itself', () {
      expect(
        resolveFallbackChain('en', locales, defaultLocale: 'en'),
        ['en'],
      );
    });

    test('single-hop fallback reaches the default', () {
      expect(
        resolveFallbackChain('pt', locales, defaultLocale: 'en'),
        ['pt', 'en'],
      );
    });

    test('multi-hop fallback preserves order', () {
      expect(
        resolveFallbackChain('pt-BR', locales, defaultLocale: 'en'),
        ['pt-BR', 'pt', 'en'],
      );
    });

    test('unknown locale still terminates at the default', () {
      expect(
        resolveFallbackChain('xx', locales, defaultLocale: 'en'),
        ['xx', 'en'],
      );
    });

    test('a non-default default locale terminates at that default', () {
      expect(
        resolveFallbackChain('pt', locales, defaultLocale: 'es'),
        ['pt', 'en', 'es'],
      );
    });

    test('fallback cycles terminate without looping', () {
      const cyclic = <String, LocaleNode>{
        'a': LocaleNode('a', fallbackCode: 'b'),
        'b': LocaleNode('b', fallbackCode: 'a'),
      };
      expect(
        resolveFallbackChain('a', cyclic, defaultLocale: 'en'),
        ['a', 'b', 'en'],
      );
    });
  });
}
