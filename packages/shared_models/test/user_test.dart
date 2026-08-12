import 'package:shared_models/shared_models.dart';
import 'package:test/test.dart';

void main() {
  group('UserProfile', () {
    test('round-trips the users/me payload', () {
      const wire = {
        'id': 'firebase-uid-123',
        'email': 'alice@example.com',
        'display_name': 'Alice',
        'role': 'moderator',
        'locale': 'pt',
      };

      final user = UserProfile.fromJson(wire);
      expect(user.id, 'firebase-uid-123');
      expect(user.email, 'alice@example.com');
      expect(user.role, 'moderator');
      expect(user.isAdmin, isFalse);

      final decoded = UserProfile.fromJson(user.toJson());
      expect(decoded.displayName, 'Alice');
      expect(decoded.locale, 'pt');
    });

    test('defaults apply when optional fields are absent', () {
      final user =
          UserProfile.fromJson(const {'id': 'u', 'email': 'b@example.com'});
      expect(user.role, 'user');
      expect(user.locale, 'en');
      expect(user.displayName, isNull);
    });

    test('rejects a payload without an id', () {
      expect(
        () => UserProfile.fromJson(const {'email': 'x@example.com'}),
        throwsFormatException,
      );
    });
  });
}
