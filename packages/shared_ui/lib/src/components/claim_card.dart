/// Claim card — one extracted claim with its verdict, verifiability,
/// rationale, and supporting evidence.
///
/// Used in analysis reports: shows the claim text, a color-coded verdict
/// badge, the model's rationale, and any gathered evidence (sources,
/// quotes, links).
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'score_meter.dart';

/// A card presenting one claim and its analysis details.
class ClaimCard extends StatelessWidget {
  const ClaimCard({
    super.key,
    required this.text,
    required this.verifiability,
    this.label,
    this.verdict,
    this.rationale,
    this.evidence = const [],
  });

  /// The claim as written in the analyzed content.
  final String text;

  /// Verifiability in `[0, 1]`.
  final double verifiability;

  /// Localized label for the score (e.g. "Verifiability").
  final String? label;

  /// Verdict label from the model, when provided.
  final String? verdict;

  /// The model's explanation of the verdict.
  final String? rationale;

  /// Supporting evidence (source/quote/link rows).
  final List<ClaimEvidenceView> evidence;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final band = scoreBandFor(verifiability.clamp(0, 1));
    final color = scoreColor(band);
    final hasVerdict = verdict != null && verdict!.isNotEmpty;

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(text, style: AppTypography.bodyLarge),
                ),
                if (hasVerdict) ...[
                  const SizedBox(width: AppSpacing.sm),
                  _VerdictBadge(verdict: verdict!, color: color),
                ],
              ],
            ),
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                Icon(
                  Icons.speed_rounded,
                  size: 15,
                  color: color,
                ),
                const SizedBox(width: 6),
                Text(
                  '${label ?? 'Verifiability'}: ${(verifiability * 100).round()}%',
                  style: AppTypography.labelMedium.copyWith(
                    color: color,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            if (rationale != null && rationale!.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                rationale!,
                style: AppTypography.bodyMedium.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            if (evidence.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              for (final item in evidence) _EvidenceRow(item: item),
            ],
          ],
        ),
      ),
    );
  }
}

/// The evidence row payload (kept widget-free for testability).
class ClaimEvidenceView {
  const ClaimEvidenceView({this.url, this.quote, this.snippet});

  final String? url;
  final String? quote;
  final String? snippet;
}

/// A color-coded verdict chip (e.g. ``false``, ``verifiable``).
class _VerdictBadge extends StatelessWidget {
  const _VerdictBadge({required this.verdict, required this.color});

  final String verdict;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(AppSpacing.radiusPill),
      ),
      child: Text(
        _humanize(verdict),
        style: AppTypography.labelMedium.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  static String _humanize(String value) {
    return value.replaceAll('_', ' ')[0].toUpperCase() +
        value.replaceAll('_', ' ').substring(1);
  }
}

/// One evidence row: a source link with its snippet.
class _EvidenceRow extends StatelessWidget {
  const _EvidenceRow({required this.item});

  final ClaimEvidenceView item;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final url = item.url;
    final hasUrl = url != null && url.isNotEmpty;
    final snippet = item.snippet ?? item.quote;

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.link_rounded,
            size: 15,
            color: colorScheme.primary,
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (hasUrl)
                  InkWell(
                    onTap: () => Clipboard.setData(ClipboardData(text: url)),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(
                          child: Text(
                            url,
                            style: AppTypography.labelMedium.copyWith(
                              color: colorScheme.primary,
                              decoration: TextDecoration.underline,
                              decorationColor: colorScheme.primary,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          Icons.copy_rounded,
                          size: 13,
                          color: colorScheme.primary,
                        ),
                      ],
                    ),
                  ),
                if (snippet != null && snippet.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    snippet,
                    style: AppTypography.bodySmall.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
