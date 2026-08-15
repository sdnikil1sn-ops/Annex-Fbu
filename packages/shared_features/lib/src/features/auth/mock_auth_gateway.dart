/// Explicit in-memory mock of [AuthGateway] for tests and local dev.
///
/// Allows tests to control the signed-in user without Firebase platform
/// channels. It is never used in production code paths.
library;

import 'dart:async';

import 'auth_gateway.dart';

/// A deterministic fake auth backend.
class MockAuthGateway implements AuthGateway {
  MockAuthGateway({AuthUser? initialUser}) : _current = initialUser;

  final StreamController<AuthUser?> _controller = StreamController.broadcast();

  AuthUser? _current;

  /// Whether [signOut] was called (test hook).
  bool signedOut = false;

  @override
  Stream<AuthUser?> get userChanges => _controller.stream;

  @override
  AuthUser? get currentUser => _current;

  @override
  Future<String?> idToken() async => null;

  @override
  Future<AuthUser> signInAnonymously() async {
    final user = AuthUser(
      uid: 'anon-${_current?.uid ?? '1'}',
      displayName: 'Guest',
    );
    _current = user;
    _controller.add(user);
    return user;
  }

  /// Test hook: credentials accepted by [signInWithEmail].
  final Map<String, String> knownAccounts = {};

  @override
  Future<AuthUser> signInWithEmail(String email, String password) async {
    final normalized = email.trim().toLowerCase();
    final expected = knownAccounts[normalized];
    if (expected == null) {
      throw StateError('user-not-found');
    }
    if (expected != password) {
      throw StateError('wrong-password');
    }
    final user = AuthUser(
      uid: 'email-$normalized',
      email: normalized,
      displayName: normalized,
    );
    _current = user;
    _controller.add(user);
    return user;
  }

  @override
  Future<AuthUser> createAccountWithEmail(String email, String password) async {
    final normalized = email.trim().toLowerCase();
    if (knownAccounts.containsKey(normalized)) {
      throw StateError('email-already-in-use');
    }
    knownAccounts[normalized] = password;
    final user = AuthUser(
      uid: 'new-$normalized',
      email: normalized,
      displayName: normalized,
    );
    _current = user;
    _controller.add(user);
    return user;
  }

  @override
  Future<AuthUser> signInWithGoogle() async {
    final user = AuthUser(
      uid: 'google-1',
      email: 'reader@example.com',
      displayName: 'Reader',
    );
    _current = user;
    _controller.add(user);
    return user;
  }

  @override
  Future<void> signOut() async {
    signedOut = true;
    _current = null;
    _controller.add(null);
  }
}
