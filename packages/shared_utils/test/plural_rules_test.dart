import 'package:shared_utils/shared_utils.dart';
import 'package:test/test.dart';

void main() {
  group('pluralCategory', () {
    test('english uses one/other', () {
      expect(pluralCategory('en', 0), 'other');
      expect(pluralCategory('en', 1), 'one');
      expect(pluralCategory('en', 2), 'other');
      expect(pluralCategory('en', 21), 'other');
    });

    test('french treats 0 and 1 as singular', () {
      expect(pluralCategory('fr', 0), 'one');
      expect(pluralCategory('fr', 1), 'one');
      expect(pluralCategory('fr', 2), 'other');
    });

    test('arabic has six categories', () {
      expect(pluralCategory('ar', 0), 'zero');
      expect(pluralCategory('ar', 1), 'one');
      expect(pluralCategory('ar', 2), 'two');
      expect(pluralCategory('ar', 5), 'few');
      expect(pluralCategory('ar', 42), 'many');
      expect(pluralCategory('ar', 101), 'other');
    });

    test('russian uses one/few/many/other', () {
      expect(pluralCategory('ru', 1), 'one');
      expect(pluralCategory('ru', 2), 'few');
      expect(pluralCategory('ru', 5), 'many');
      expect(pluralCategory('ru', 11), 'many');
      expect(pluralCategory('ru', 21), 'one');
      expect(pluralCategory('ru', 22), 'few');
      expect(pluralCategory('ru', 25), 'many');
    });

    test('languages without number use other', () {
      expect(pluralCategory('ja', 1), 'other');
      expect(pluralCategory('ja', 10), 'other');
      expect(pluralCategory('zh', 1), 'other');
    });

    test('region tags resolve by base language', () {
      expect(pluralCategory('pt-BR', 1), 'one');
      expect(pluralCategory('en-US', 1), 'one');
      expect(pluralCategory('ar-EG', 0), 'zero');
    });

    test('unknown locales fall back to one/other', () {
      expect(pluralCategory('xx', 1), 'one');
      expect(pluralCategory('xx', 3), 'other');
    });
  });
}
