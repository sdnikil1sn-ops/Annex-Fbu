/// Score meter — the credibility indicator used across ANNEX surfaces.
///
/// Renders a `0..1` score as a labeled ring/bar with a semantic color
/// (danger / warning / success bands) and an optional accessibility label.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// Visual bands for a credibility score.
enum ScoreBand { low, medium, high }

/// Maps a `0..1` score to its semantic color band.
ScoreBand scoreBandFor(double score) {
  if (score >= 0.66) return ScoreBand.high;
  if (score >= 0.33) return ScoreBand.medium;
  return ScoreBand.low;
}

/// The color for a score band.
Color scoreColor(ScoreBand band) {
  switch (band) {
    case ScoreBand.high:
      return AppColors.success;
    case ScoreBand.medium:
      return AppColors.warning;
    case ScoreBand.low:
      return AppColors.danger;
  }
}

/// A circular credibility score meter.
class ScoreMeter extends StatelessWidget {
  const ScoreMeter({
    super.key,
    required this.score,
    this.size = 96,
    this.label,
  });

  /// Credibility score in `[0, 1]`.
  final double score;

  /// Diameter of the ring in logical pixels.
  final double size;

  /// Optional semantic label (e.g. a localized "Credibility score" string).
  final String? label;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final clamped = score.clamp(0.0, 1.0);
    final band = scoreBandFor(clamped);
    final color = scoreColor(band);
    final percentage = (clamped * 100).round();

    return Semantics(
      label: label == null
          ? 'Credibility score $percentage%'
          : '$label $percentage%',
      container: true,
      excludeSemantics: true,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: size,
            height: size,
            child: CustomPaint(
              painter: _ScoreRingPainter(
                progress: clamped,
                color: color,
                trackColor: colorScheme.surfaceContainerHighest,
                strokeWidth: size / 10,
              ),
              child: Center(
                child: Text(
                  '$percentage%',
                  style: AppTypography.headlineMedium.copyWith(
                    color: color,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
          if (label != null) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              label!,
              style: AppTypography.labelMedium.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Paints the score ring (arc) with rounded caps.
class _ScoreRingPainter extends CustomPainter {
  _ScoreRingPainter({
    required this.progress,
    required this.color,
    required this.trackColor,
    required this.strokeWidth,
  });

  final double progress;
  final Color color;
  final Color trackColor;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (math.min(size.width, size.height) - strokeWidth) / 2;
    final track = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..color = trackColor;
    canvas.drawCircle(center, radius, track);

    final arc = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = color;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      2 * math.pi * progress.clamp(0.0, 1.0),
      false,
      arc,
    );
  }

  @override
  bool shouldRepaint(_ScoreRingPainter oldDelegate) {
    return oldDelegate.progress != progress ||
        oldDelegate.color != color ||
        oldDelegate.trackColor != trackColor;
  }
}
