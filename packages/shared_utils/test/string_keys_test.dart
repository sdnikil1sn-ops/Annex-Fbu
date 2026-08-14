import 'package:shared_utils/shared_utils.dart';
import 'package:test/test.dart';

void main() {
  group('StringKeys registry', () {
    test('keys are well-formed namespace.key strings', () {
      for (final key in StringKeys.all) {
        expect(StringKeys.isValid(key), isTrue, reason: '$key must be valid');
        expect(StringKeys.isKnown(key), isTrue, reason: '$key must be known');
      }
    });

    test('keys cover the namespaces served by the backend', () {
      final namespaces = StringKeys.all.map(StringKeys.namespaceOf).toSet();
      expect(
          namespaces,
          containsAll(<String>{
            'common',
            'analysis',
            'auth',
            'errors',
            'lessons',
            'classes',
            'suggestions',
            'sources',
            'settings'
          }));
    });

    test('isValid rejects malformed keys', () {
      expect(StringKeys.isValid('nokey'), isFalse); // no dot
      expect(StringKeys.isValid('Namespace.key'), isFalse); // uppercase
      expect(StringKeys.isValid('common.'), isFalse); // empty key
      expect(StringKeys.isValid(''), isFalse);
    });

    test('isKnown rejects unregistered keys', () {
      expect(StringKeys.isKnown('common.not_a_real_key'), isFalse);
    });

    test('namespaceOf returns the namespace prefix', () {
      expect(StringKeys.namespaceOf(StringKeys.commonCancel), 'common');
      expect(StringKeys.namespaceOf('bad'), isNull);
    });

    test('every key is unique', () {
      expect(StringKeys.all.toSet().length, StringKeys.all.length);
    });
  });
}
