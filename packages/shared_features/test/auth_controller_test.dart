import 'package:flutter_test/flutter_test.dart';
import 'package:shared_features/shared_features.dart';

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
    final gateway = MockAuthGateway();
    final controller = AuthController(gateway);
    addTearDown(controller.dispose);

    await controller.createAccountWithEmail('a@example.com', 'secret123');
    await controller.signInWithEmail('a@example.com', 'secret123');

    expect(controller.user!.email, 'a@example.com');
  });

  test('wrong password is rejected and surfaces the error code', () async {
    final gateway = MockAuthGateway();
    final controller = AuthController(gateway);
    addTearDown(controller.dispose);

    await controller.createAccountWithEmail('a@example.com', 'secret123');
    await controller.signOut();
    await controller.signInWithEmail('a@example.com', 'wrongpass');

    expect(controller.user, isNull);
    expect(controller.errorCode, 'wrong-password');
    expect(controller.error, isNotNull);
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
