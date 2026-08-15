/// Page header — the consistent title block at the top of every page.
///
/// Replaces bare AppBar titles with a titled + subtitled header so pages
/// read like a product, not a list of screens. Optional [actions] render
/// on the trailing edge (desktop-friendly), while the whole header wraps
/// gracefully on narrow viewports.
library;

import 'package:flutter/material.dart';

import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// The standard ANNEX page header.
class PageHeader extends StatelessWidget {
  const PageHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.icon,
    this.actions = const [],
  });

  /// The page title.
  final String title;

  /// Optional supporting line under the title.
  final String? subtitle;

  /// Optional leading glyph shown in a soft brand chip.
  final IconData? icon;

  /// Optional trailing widgets (buttons, toggles) for wide layouts.
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        if (icon != null) ...[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
            ),
            child: Icon(icon, size: 22, color: colorScheme.primary),
          ),
          const SizedBox(width: AppSpacing.md),
        ],
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: AppTypography.headlineLarge),
              if (subtitle != null && subtitle!.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  style: AppTypography.bodyMedium.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (actions.isNotEmpty) ...[
          const SizedBox(width: AppSpacing.md),
          Wrap(spacing: AppSpacing.xs, children: actions),
        ],
      ],
    );
  }
}
