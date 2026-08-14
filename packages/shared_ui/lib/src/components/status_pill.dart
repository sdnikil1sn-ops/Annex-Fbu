/// Status pill — a small rounded label for an analysis lifecycle state.
library;

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// The lifecycle state shown by a [StatusPill].
enum PillState { pending, processing, success, failure, neutral }

/// Maps a pill state to its foreground color.
///
/// [neutral] resolves against the ambient theme (the other states are
/// semantic and theme-independent).
Color pillColor(PillState state, ColorScheme colorScheme) {
  switch (state) {
    case PillState.pending:
      return AppColors.info;
    case PillState.processing:
      return AppColors.primary;
    case PillState.success:
      return AppColors.success;
    case PillState.failure:
      return AppColors.danger;
    case PillState.neutral:
      return colorScheme.onSurfaceVariant;
  }
}

/// A small rounded status label.
class StatusPill extends StatelessWidget {
  const StatusPill({
    super.key,
    required this.label,
    this.state = PillState.neutral,
  });

  /// The localized label to display.
  final String label;

  /// The semantic state driving the color.
  final PillState state;

  @override
  Widget build(BuildContext context) {
    final color = pillColor(state, Theme.of(context).colorScheme);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppSpacing.radiusPill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (state == PillState.processing) ...[
            SizedBox.square(
              dimension: 10,
              child: CircularProgressIndicator(strokeWidth: 2, color: color),
            ),
            const SizedBox(width: AppSpacing.xxs),
          ],
          Flexible(
            child: Text(
              label,
              style: AppTypography.labelMedium.copyWith(color: color),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}
