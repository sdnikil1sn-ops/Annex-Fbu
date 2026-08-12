/// Authentication gateway (ADR-0005).
///
/// The app depends on [AuthGateway]; production uses [FirebaseAuthGateway]
/// (Firebase Auth SDK: anonymous, email/password, Google) and tests use
/// the explicit mock. The gateway emits [AuthUser] state changes so the UI
/// can react to sign-in and sign-out.
library;

import 'package:firebase_auth/firebase_auth.dart' as fa;
import 'package:google_sign_in/google_sign_in.dart';

/// A signed-in user as the app understands it.
class AuthUser {
  const AuthUser({required this.uid, this.email, this.displayName});

  final String uid;
  final String? email;
  final String? displayName;

  @override
  bool operator ==(Object other) =>
      other is AuthUser && other.uid == uid && other.email == email;

  @override
  int get hashCode => Object.hash(uid, email);
}

/// The authentication surface used by the app.
abstract interface class AuthGateway {
  /// Emits the current user (null when signed out) on changes.
  Stream<AuthUser?> get userChanges;

  /// The currently signed-in user, or null.
  AuthUser? get currentUser;

  Future<AuthUser> signInAnonymously();

  Future<AuthUser> signInWithEmail(String email, String password);

  Future<AuthUser> signInWithGoogle();

  Future<void> signOut();
}

/// Firebase Auth SDK implementation (anonymous, email/password, Google).
class FirebaseAuthGateway implements AuthGateway {
  FirebaseAuthGateway({fa.FirebaseAuth? auth, GoogleSignIn? googleSignIn})
    : _auth = auth ?? fa.FirebaseAuth.instance,
      _googleSignIn = googleSignIn ?? GoogleSignIn();

  final fa.FirebaseAuth _auth;
  final GoogleSignIn _googleSignIn;

  @override
  Stream<AuthUser?> get userChanges =>
      _auth.authStateChanges().map(_fromFirebase);

  @override
  AuthUser? get currentUser => _fromFirebase(_auth.currentUser);

  @override
  Future<AuthUser> signInAnonymously() async {
    final credential = await _auth.signInAnonymously();
    return _fromFirebase(credential.user)!;
  }

  @override
  Future<AuthUser> signInWithEmail(String email, String password) async {
    final credential = await _auth.signInWithEmailAndPassword(
      email: email,
      password: password,
    );
    return _fromFirebase(credential.user)!;
  }

  @override
  Future<AuthUser> signInWithGoogle() async {
    final account = await _googleSignIn.signIn();
    if (account == null) {
      throw StateError('Google sign-in was cancelled');
    }
    final authentication = await account.authentication;
    final credential = fa.GoogleAuthProvider.credential(
      idToken: authentication.idToken,
      accessToken: authentication.accessToken,
    );
    final result = await _auth.signInWithCredential(credential);
    return _fromFirebase(result.user)!;
  }

  @override
  Future<void> signOut() async {
    await Future.wait([_auth.signOut(), _googleSignIn.signOut()]);
  }

  static AuthUser? _fromFirebase(fa.User? user) {
    if (user == null) return null;
    return AuthUser(
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
    );
  }
}
