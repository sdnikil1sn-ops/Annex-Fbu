/// Auth state controller.
///
/// Listens to the [AuthGateway]'s user stream and exposes the current
/// user plus a busy flag for sign-in actions.
library;

import 'dart:async';

import 'package:flutter/foundation.dart';

import 'auth_gateway.dart';

/// Drives authentication state for the app shell.
class AuthController extends ChangeNotifier {
  AuthController(AuthGateway gateway) : _gateway = gateway {
    _subscription = gateway.userChanges.listen(_onUserChanged);
    _user = gateway.currentUser;
  }

  final AuthGateway _gateway;
  StreamSubscription<AuthUser?>? _subscription;

  AuthUser? _user;
  bool _busy = false;

  /// The signed-in user, or null.
  AuthUser? get user => _user;

  /// Whether a sign-in/sign-out action is in flight.
  bool get busy => _busy;

  /// The last action error, if any (e.g. a cancelled Google flow).
  String? get error => _error;
  String? _error;

  /// Clear the last action error (e.g. when switching auth modes).
  void clearError() {
    if (_error == null) return;
    _error = null;
    notifyListeners();
  }

  void _onUserChanged(AuthUser? user) {
    _user = user;
    notifyListeners();
  }

  /// Sign in anonymously (available without credentials).
  Future<void> signInAnonymously() =>
      _guard(() => _gateway.signInAnonymously());

  /// Sign in with email/password.
  Future<void> signInWithEmail(String email, String password) =>
      _guard(() => _gateway.signInWithEmail(email, password));

  /// Create a new email/password account and sign it in.
  Future<void> createAccountWithEmail(String email, String password) =>
      _guard(() => _gateway.createAccountWithEmail(email, password));

  /// Sign in with Google.
  Future<void> signInWithGoogle() => _guard(() => _gateway.signInWithGoogle());

  /// Sign out the current user.
  Future<void> signOut() => _guard(() => _gateway.signOut());

  Future<void> _guard(Future<Object?> Function() action) async {
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      await action();
    } catch (error) {
      // Surface the failure instead of leaking an unhandled zone error
      // (e.g. when the user cancels the Google sign-in sheet).
      _error = error.toString();
      notifyListeners();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}
