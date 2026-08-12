/// Claim card — one extracted claim with its verifiability pill.
///
/// Used in analysis reports: shows the claim text, a localized label, and
/// a color-coded verifiability badge.
library;

import 'package:flutter/material.dart';

import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'score_meter.dart';

/// A card presenting one claim and its verifiability score.
class ClaimCard extends StatelessWidget {
  const ClaimCard({
    super.key,
    required this.text,
    required this.verifiability,
    this.label,
  });

  /// The claim as written in the analyzed content.
  final String text;

  /// Verifiability in `[0, 1]`.
  final double verifiability;

  /// Localized label for the score (e.g. "Verifiability").
  final String? label;

  @override
  Widget build(BuildContext context) {
    final band = scoreBandFor(verifiability.clamp(0, 1));
    final color = scoreColor(band);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(text, style: AppTypography.bodyLarge),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    '${label ?? 'Verifiability'}: ${(verifiability * 100).round()}%',
                    style: AppTypography.labelMedium.copyWith(color: color),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.sm,
                vertical: AppSpacing.xxs,
              ),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(AppSpacing.radiusPill),
              ),
              child: Text(
                _bandLabel(band),
                style: AppTypography.labelMedium.copyWith(color: color),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _bandLabel(ScoreBand band) {
    switch (band) {
      case ScoreBand.high:
        return 'High';
      case ScoreBand.medium:
        return 'Medium';
      case ScoreBand.low:
        return 'Low';
    }
  }
}
