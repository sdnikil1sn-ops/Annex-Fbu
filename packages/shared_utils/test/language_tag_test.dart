import 'package:shared_utils/shared_utils.dart';
import 'package:test/test.dart';

void main() {
  group('isValidLanguageTag', () {
    test('accepts the seeded locale shapes', () {
      expect(isValidLanguageTag('en'), isTrue);
      expect(isValidLanguageTag('pt'), isTrue);
      expect(isValidLanguageTag('pt-BR'), isTrue);
      expect(isValidLanguageTag('zh-Hans'), isTrue);
    });

    test('is case-insensitive', () {
      expect(isValidLanguageTag('PT'), isTrue);
      expect(isValidLanguageTag('Pt-BR'), isTrue);
    });

    test('rejects malformed tags', () {
      expect(isValidLanguageTag(''), isFalse);
      expect(isValidLanguageTag('en_US'), isFalse); // underscore
      expect(isValidLanguageTag('1en'), isFalse); // digit first
      expect(isValidLanguageTag('en--US'), isFalse); // empty subtag
      expect(isValidLanguageTag('a'), isFalse); // too short
      expect(isValidLanguageTag('toolongtag'), isFalse); // > 3 letters
    });
  });

  group('canonicalLanguageTag', () {
    test('lowercases and trims', () {
      expect(canonicalLanguageTag(' PT-BR '), 'pt-br');
      expect(canonicalLanguageTag('en'), 'en');
    });
  });
}
