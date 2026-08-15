/// Brand mark — the ANNEX logo glyph.
///
/// A custom-painted monogram: a two-tone ring (vibrant purple top-left,
/// metallic grey bottom-right) enclosing an "an" wordmark — the "a" in a
/// purple→blue gradient and the "n" in a brushed-metal grey gradient.
/// Used on the sign-in hero and the app sidebar.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';

/// The ANNEX logo mark.
class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.size = 40, this.borderRadius});

  final double size;

  /// Legacy corner radius; retained for API compatibility (the new mark
  /// is a ring, so this is unused).
  final double? borderRadius;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _AnnexMarkPainter(size: size),
      ),
    );
  }
}

/// Paints the two-tone ring and the gradient "an" wordmark.
class _AnnexMarkPainter extends CustomPainter {
  const _AnnexMarkPainter({required this.size});

  final double size;

  @override
  void paint(Canvas canvas, Size canvasSize) {
    final center = Offset(canvasSize.width / 2, canvasSize.height / 2);
    final radius = size * 0.46;
    final ringWidth = size * 0.062;

    // --- Ring: purple arc (top-left → top → right) ---
    final purpleRect = Rect.fromCircle(center: center, radius: radius);
    final purplePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = ringWidth
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        startAngle: _rad(135),
        endAngle: _rad(315),
        colors: [
          AppColors.logoPurple.withValues(alpha: 0),
          AppColors.logoPurple,
          AppColors.logoBlue,
          AppColors.logoPurple.withValues(alpha: 0),
        ],
        stops: const [0.0, 0.35, 0.75, 1.0],
      ).createShader(purpleRect);
    canvas.drawArc(
      purpleRect,
      _rad(135),
      _rad(180),
      false,
      purplePaint,
    );

    // --- Ring: metallic grey arc (bottom-right → bottom → left) ---
    final greyPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = ringWidth
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        startAngle: _rad(315),
        endAngle: _rad(495),
        colors: [
          AppColors.logoGrey.withValues(alpha: 0),
          AppColors.logoGrey,
          AppColors.logoGreyLight,
          AppColors.logoGrey.withValues(alpha: 0),
        ],
        stops: const [0.0, 0.35, 0.75, 1.0],
      ).createShader(purpleRect);
    canvas.drawArc(
      purpleRect,
      _rad(315),
      _rad(180),
      false,
      greyPaint,
    );

    // --- Wordmark: gradient "an" ---
    _paintLetter(
      canvas,
      canvasSize,
      'a',
      _aPaint(center),
    );
    _paintLetter(
      canvas,
      canvasSize,
      'n',
      _nPaint(center),
    );
  }

  static double _rad(num degrees) => degrees * math.pi / 180;

  /// Paints one lowercase letter, centered as a pair around [center].
  void _paintLetter(
    Canvas canvas,
    Size canvasSize,
    String letter,
    Paint paint,
  ) {
    final fontSize = size * 0.5;
    final painter = TextPainter(
      text: TextSpan(
        text: letter,
        style: TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.w800,
          fontStyle: FontStyle.italic,
          height: 1,
          letterSpacing: -size * 0.03,
          foreground: paint,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();

    // Both letters share the same cap-height box so the pair reads as one
    // wordmark; "n" sits slightly lower, mirroring a rounded "a" tail.
    final width = size * 0.24;
    final yOffset = letter == 'n' ? size * 0.02 : 0.0;
    final dx = letter == 'a' ? -size * 0.155 : size * 0.155;
    painter.paint(
      canvas,
      Offset(
        canvasSize.width / 2 + dx - painter.width / 2 + width * 0.06,
        canvasSize.height / 2 - painter.height / 2 + yOffset,
      ),
    );
  }

  /// Purple→blue gradient for the "a".
  Paint _aPaint(Offset center) {
    return Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [AppColors.logoPurple, AppColors.logoBlue],
      ).createShader(
        Rect.fromCenter(center: center, width: size, height: size),
      );
  }

  /// Brushed-metal vertical gradient for the "n".
  Paint _nPaint(Offset center) {
    return Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [AppColors.logoGreyLight, AppColors.logoGrey, AppColors.logoGreyDeep],
        stops: const [0.0, 0.55, 1.0],
      ).createShader(
        Rect.fromCenter(center: center, width: size, height: size),
      );
  }

  @override
  bool shouldRepaint(_AnnexMarkPainter oldDelegate) => oldDelegate.size != size;
}
