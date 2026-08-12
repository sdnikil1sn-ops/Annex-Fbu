/// Color tokens — the single source of truth for ANNEX colors.
///
/// Components and themes consume these tokens; raw color values never
/// appear in widgets. Both themes derive from the same seed palette and
/// meet WCAG 2.1 AA contrast for text-on-background.
library;

import 'package:flutter/material.dart';

/// The ANNEX color palette, independent of light/dark mode.
abstract final class AppColors {
  // Brand (purple family — "Learn Before You Believe").
  static const Color primary = Color(0xFF5B3DF5);
  static const Color primaryContainer = Color(0xFFE8E3FF);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color onPrimaryContainer = Color(0xFF22005D);

  // Semantic.
  static const Color success = Color(0xFF1B7F4D);
  static const Color warning = Color(0xFF9A6700);
  static const Color danger = Color(0xFFBA1A1A);
  static const Color info = Color(0xFF00639B);

  // Surfaces — light.
  static const Color backgroundLight = Color(0xFFFDFBFF);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color surfaceVariantLight = Color(0xFFE7E0EC);
  static const Color onSurfaceLight = Color(0xFF1C1B1F);
  static const Color onSurfaceVariantLight = Color(0xFF49454F);
  static const Color outlineLight = Color(0xFF79747E);

  // Surfaces — dark.
  static const Color backgroundDark = Color(0xFF141218);
  static const Color surfaceDark = Color(0xFF1C1B20);
  static const Color surfaceVariantDark = Color(0xFF49454F);
  static const Color onSurfaceDark = Color(0xFFE6E0E9);
  static const Color onSurfaceVariantDark = Color(0xFFCAC4D0);
  static const Color outlineDark = Color(0xFF938F99);
}
