import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('Source', () {
    test('round-trips the profile payload from the API', () {
      final source = Source.fromJson(const {
        'id': 'src-1',
        'domain': 'reuters.com',
        'name': 'Reuters',
        'country': 'US',
        'language': 'en',
        'category': 'news',
        'score': 0.92,
        'signals': {'editorial_standards': 'high', 'fact_checking': 'strong'},
        'model': 'seed-v1',
        'computed_at': '2026-08-12T10:00:00Z',
        'community': {
          'count': 3,
          'average': 4.5,
          'my_rating': 5,
        },
      });

      expect(source.id, 'src-1');
      expect(source.domain, 'reuters.com');
      expect(source.name, 'Reuters');
      expect(source.score, 0.92);
      expect(source.signals['fact_checking'], 'strong');
      expect(source.model, 'seed-v1');
      expect(source.computedAt, DateTime.parse('2026-08-12T10:00:00Z'));
      expect(source.community.count, 3);
      expect(source.community.average, 4.5);
      expect(source.community.myRating, 5);
      expect(source.community.hasRated, isTrue);

      final decoded = Source.fromJson(source.toJson());
      expect(decoded.domain, source.domain);
      expect(decoded.toJson(), source.toJson());
    });

    test('defaults apply when community and signals are absent', () {
      final source = Source.fromJson(const {
        'id': 'src-2',
        'domain': 'snopes.com',
        'score': 0.95,
      });

      expect(source.name, isNull);
      expect(source.signals, isEmpty);
      expect(source.community.count, 0);
      expect(source.community.average, isNull);
      expect(source.community.hasRated, isFalse);
    });

    test('rejects a source without an id or domain', () {
      expect(
          () => Source.fromJson(const {'domain': 'x'}), throwsFormatException);
      expect(() => Source.fromJson(const {'id': 'x'}), throwsFormatException);
    });
  });

  group('SourceCommunity', () {
    test('round-trips the aggregate payload', () {
      final community = SourceCommunity.fromJson(const {
        'count': 7,
        'average': 3.8,
        'my_rating': null,
      });

      expect(community.count, 7);
      expect(community.average, 3.8);
      expect(community.hasRated, isFalse);

      final decoded = SourceCommunity.fromJson(community.toJson());
      expect(decoded.toJson(), community.toJson());
    });
  });
}
