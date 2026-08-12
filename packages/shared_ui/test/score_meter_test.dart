import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_ui/shared_ui.dart';

void main() {
  group('scoreBandFor', () {
    test('bands map scores to semantic levels', () {
      expect(scoreBandFor(0.9), ScoreBand.high);
      expect(scoreBandFor(0.66), ScoreBand.high);
      expect(scoreBandFor(0.5), ScoreBand.medium);
      expect(scoreBandFor(0.33), ScoreBand.medium);
      expect(scoreBandFor(0.1), ScoreBand.low);
    });
  });

  group('ScoreMeter', () {
    testWidgets('renders the percentage and semantic label', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ScoreMeter(score: 0.75, label: 'Credibility'),
          ),
        ),
      );

      expect(find.text('75%'), findsOneWidget);
      expect(find.text('Credibility'), findsOneWidget);
      final semantics = tester.getSemantics(find.byType(ScoreMeter));
      expect(semantics.label, 'Credibility 75%');
    });

    testWidgets('clamps out-of-range scores', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(home: Scaffold(body: ScoreMeter(score: 1.5))),
      );
      expect(find.text('100%'), findsOneWidget);
    });
  });
}
