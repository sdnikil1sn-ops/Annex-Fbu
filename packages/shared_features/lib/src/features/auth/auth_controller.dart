/// Auth state controller.
///
/// Listens to the [AuthGateway]'s user stream and exposes the current
/// user plus a busy flag for sign-in actions.
library;

import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart' as fa;
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

  /// The machine-readable error code of the last failure, when available
  /// (e.g. ``wrong-password`` from a FirebaseAuthException).
  String? get errorCode => _errorCode;
  String? _errorCode;

  /// Clear the last action error (e.g. when switching auth modes).
  void clearError() {
    if (_error == null && _errorCode == null) return;
    _error = null;
    _errorCode = null;
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
    _errorCode = null;
    notifyListeners();
    try {
      await action();
    } catch (error) {
      // Surface the failure instead of leaking an unhandled zone error
      // (e.g. when the user cancels the Google sign-in sheet).
      _error = error.toString();
      _errorCode = _extractCode(error);
      notifyListeners();
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Best-effort extraction of a Firebase error code.
  ///
  /// FirebaseAuthException exposes a structured ``code``; StateError (used
  /// by the debug mock) carries the code as its message.
  static String? _extractCode(Object error) {
    final code = switch (error) {
      fa.FirebaseAuthException(:final code) => code,
      StateError(:final message) => message,
      _ => null,
    };
    // Firebase messages look like "firebase_auth/wrong-password" — keep the
    // segment after the slash (or the whole code) as the stable identifier.
    if (code == null) return null;
    return code.contains('/') ? code.split('/').last : code;
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}
