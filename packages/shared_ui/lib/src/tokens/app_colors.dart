/// Color tokens — the single source of truth for ANNEX colors.
///
/// Components and themes consume these tokens; raw color values never
/// appear in widgets. Both themes derive from the same seed palette and
/// meet WCAG 2.1 AA contrast for text-on-background.
library;

import 'package:flutter/material.dart';

/// The ANNEX color palette, independent of light/dark mode.
abstract final class AppColors {
  // Brand — deep indigo/violet ("Learn Before You Believe").
  static const Color primary = Color(0xFF5B3DF5);
  static const Color primaryDark = Color(0xFF4530C8);
  static const Color primaryContainer = Color(0xFFE9E4FF);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color onPrimaryContainer = Color(0xFF1E1054);

  // Accent — vivid teal (education / trust).
  static const Color accent = Color(0xFF00BFA5);
  static const Color accentContainer = Color(0xFFD5FBF3);
  static const Color onAccent = Color(0xFF00382F);

  // Brand gradients.
  static const Color gradientStart = Color(0xFF5B3DF5);
  static const Color gradientEnd = Color(0xFF8B5CF6);
  static const Color gradientSoftStart = Color(0xFF7C6BF6);
  static const Color gradientSoftEnd = Color(0xFF9C6BF2);

  // Logo monogram (two-tone ring + gradient wordmark).
  static const Color logoPurple = Color(0xFF8A2BE2);
  static const Color logoBlue = Color(0xFF4F46E5);
  static const Color logoGrey = Color(0xFF6E6A75);
  static const Color logoGreyLight = Color(0xFFB9B4C2);
  static const Color logoGreyDeep = Color(0xFF3F3B47);

  // Sidebar (dark rail) — deep indigo-black.
  static const Color sidebarBackground = Color(0xFF131020);
  static const Color sidebarSurface = Color(0xFF1D1930);
  static const Color sidebarActive = Color(0xFF2A2350);
  static const Color onSidebar = Color(0xFFEDEAF9);
  static const Color onSidebarMuted = Color(0xFF9C95BE);

  // Semantic.
  static const Color success = Color(0xFF16825D);
  static const Color warning = Color(0xFF9A6700);
  static const Color danger = Color(0xFFC62828);
  static const Color info = Color(0xFF00639B);

  // Surfaces — light.
  static const Color backgroundLight = Color(0xFFF8F7FC);
  static const Color surfaceLight = Color(0xFFFFFFFF);
  static const Color surfaceVariantLight = Color(0xFFF0EDF8);
  static const Color onSurfaceLight = Color(0xFF1B1B22);
  static const Color onSurfaceVariantLight = Color(0xFF555160);
  static const Color outlineLight = Color(0xFFD8D5E3);

  // Surfaces — dark.
  static const Color backgroundDark = Color(0xFF121016);
  static const Color surfaceDark = Color(0xFF1C1A23);
  static const Color surfaceVariantDark = Color(0xFF2A2733);
  static const Color onSurfaceDark = Color(0xFFECE8F2);
  static const Color onSurfaceVariantDark = Color(0xFFBDB8CC);
  static const Color outlineDark = Color(0xFF3A3648);
}
