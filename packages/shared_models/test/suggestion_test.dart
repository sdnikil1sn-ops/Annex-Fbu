import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('MissingKey', () {
    test('round-trips the missing payload from the API', () {
      final missing = MissingKey.fromJson(const {
        'namespace': 'common',
        'key': 'retry',
        'english': 'Retry',
      });

      expect(missing.namespace, 'common');
      expect(missing.key, 'retry');
      expect(missing.englishValue, 'Retry');
      expect(missing.fullKey, 'common.retry');

      final decoded = MissingKey.fromJson(missing.toJson());
      expect(decoded.fullKey, missing.fullKey);
      expect(decoded.toJson(), missing.toJson());
    });

    test('rejects a missing key without a namespace or key', () {
      expect(
          () => MissingKey.fromJson(const {'key': 'x'}), throwsFormatException);
      expect(() => MissingKey.fromJson(const {'namespace': 'x'}),
          throwsFormatException);
    });
  });

  group('TranslationSuggestion', () {
    test('round-trips the pending submission payload', () {
      final suggestion = TranslationSuggestion.fromJson(const {
        'id': 's0000000-0000-4000-8000-000000000001',
        'locale': 'pt',
        'namespace': 'lessons',
        'key': 'complete',
        'value': 'Concluir',
        'plural_rule': 'none',
        'suggested_by': 'u0000000-0000-4000-8000-000000000001',
        'status': 'pending',
        'created_at': '2026-08-14T10:00:00Z',
      });

      expect(suggestion.id, 's0000000-0000-4000-8000-000000000001');
      expect(suggestion.locale, 'pt');
      expect(suggestion.fullKey, 'lessons.complete');
      expect(suggestion.value, 'Concluir');
      expect(suggestion.status, 'pending');
      expect(suggestion.isPending, isTrue);
      expect(suggestion.createdAt, DateTime.parse('2026-08-14T10:00:00Z'));

      final decoded = TranslationSuggestion.fromJson(suggestion.toJson());
      expect(decoded.value, suggestion.value);
      expect(decoded.toJson(), suggestion.toJson());
    });

    test('round-trips an approved suggestion', () {
      final suggestion = TranslationSuggestion.fromJson(const {
        'id': 's0000000-0000-4000-8000-000000000002',
        'locale': 'pt',
        'namespace': 'common',
        'key': 'retry',
        'value': 'Tentar novamente',
        'plural_rule': 'none',
        'status': 'approved',
        'created_at': '2026-08-14T11:00:00Z',
      });

      expect(suggestion.isPending, isFalse);
      expect(suggestion.pluralRule, 'none');
      expect(suggestion.suggestedBy, isNull);
    });

    test('rejects a suggestion without an id, key, or value', () {
      expect(
        () => TranslationSuggestion.fromJson(const {
          'locale': 'pt',
          'namespace': 'x',
          'key': 'k',
          'value': 'v',
        }),
        throwsFormatException,
      );
      expect(
        () => TranslationSuggestion.fromJson(const {
          'id': 'x',
          'locale': 'pt',
          'namespace': 'x',
          'value': 'v',
        }),
        throwsFormatException,
      );
      expect(
        () => TranslationSuggestion.fromJson(const {
          'id': 'x',
          'locale': 'pt',
          'namespace': 'x',
          'key': 'k',
        }),
        throwsFormatException,
      );
    });
  });
}
