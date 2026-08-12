/// User models (ADR-0005).
///
/// Mirrors the backend `users`/`profiles` shapes surfaced through
/// `GET /v1/users/me`: Firebase UID identity plus role and locale.
library;

/// The authenticated caller as hydrated by the backend.
class UserProfile {
  const UserProfile({
    required this.id,
    required this.email,
    this.displayName,
    this.role = 'user',
    this.locale = 'en',
  });

  /// The Firebase UID (also the backend user id).
  final String id;

  final String email;

  /// Optional display name from the identity provider.
  final String? displayName;

  /// RBAC role: `user`, `moderator`, or `admin`.
  final String role;

  /// Current UI language code.
  final String locale;

  bool get isAdmin => role == 'admin';

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    final id = json['id'];
    final email = json['email'];
    if (id is! String || id.isEmpty) {
      throw const FormatException('User requires an id');
    }
    if (email is! String) {
      throw const FormatException('User requires an email');
    }
    return UserProfile(
      id: id,
      email: email,
      displayName: json['display_name'] as String?,
      role: json['role'] as String? ?? 'user',
      locale: json['locale'] as String? ?? 'en',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'email': email,
        'display_name': displayName,
        'role': role,
        'locale': locale,
      };
}
