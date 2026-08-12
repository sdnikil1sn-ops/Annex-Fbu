import 'package:annex_mobile/features/auth/auth_controller.dart';
import 'package:annex_mobile/features/auth/mock_auth_gateway.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('starts signed out and reacts to anonymous sign-in', () async {
    final gateway = MockAuthGateway();
    final controller = AuthController(gateway);
    addTearDown(controller.dispose);

    expect(controller.user, isNull);

    await controller.signInAnonymously();

    expect(controller.user, isNotNull);
    expect(controller.user!.uid, startsWith('anon-'));
  });

  test('email sign-in exposes the identity', () async {
    final controller = AuthController(MockAuthGateway());
    addTearDown(controller.dispose);

    await controller.signInWithEmail('a@example.com', 'secret');

    expect(controller.user!.email, 'a@example.com');
  });

  test('sign-out clears the user and notifies', () async {
    final gateway = MockAuthGateway();
    final controller = AuthController(gateway);
    addTearDown(controller.dispose);

    await controller.signInAnonymously();
    await controller.signOut();

    expect(controller.user, isNull);
    expect(gateway.signedOut, isTrue);
  });

  test('busy flag is true during sign-in', () async {
    final gateway = MockAuthGateway();
    final controller = AuthController(gateway);
    addTearDown(controller.dispose);

    final future = controller.signInAnonymously();
    expect(controller.busy, isTrue);
    await future;
    expect(controller.busy, isFalse);
  });
}
