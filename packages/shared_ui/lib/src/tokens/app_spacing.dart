/// Spacing and radius tokens — a 4 px base unit.
library;

/// The ANNEX spacing and corner-radius scale.
abstract final class AppSpacing {
  // Space scale.
  static const double xxs = 4;
  static const double xs = 8;
  static const double sm = 12;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  // Corner radii.
  static const double radiusSm = 8;
  static const double radiusMd = 12;
  static const double radiusLg = 16;
  static const double radiusXl = 24;
  static const double radiusPill = 999;

  // Layout.
  /// Maximum content width for desktop pages (keeps long lines readable).
  static const double pageMaxWidth = 1040;
}
