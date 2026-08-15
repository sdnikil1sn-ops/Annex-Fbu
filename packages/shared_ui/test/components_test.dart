import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_ui/shared_ui.dart';

void main() {
  group('AppButton', () {
    testWidgets('shows the label and fires onPressed', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AppButton(label: 'Analyze', onPressed: () => tapped = true),
          ),
        ),
      );

      expect(find.text('Analyze'), findsOneWidget);
      await tester.tap(find.text('Analyze'));
      expect(tapped, isTrue);
    });

    testWidgets('busy state disables the button and shows a spinner',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: AppButton(label: 'Running', busy: true)),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      final button = tester.widget<FilledButton>(find.byType(FilledButton));
      expect(button.onPressed, isNull);
    });
  });

  group('ClaimCard', () {
    testWidgets('renders claim text and verifiability', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ClaimCard(text: 'The sky is blue', verifiability: 0.9),
          ),
        ),
      );

      expect(find.text('The sky is blue'), findsOneWidget);
      expect(find.text('Verifiability: 90%'), findsOneWidget);
    });

    testWidgets('renders verdict, rationale, and evidence', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ClaimCard(
              text: 'Vaccines cause autism',
              verifiability: 1.0,
              verdict: 'false',
              rationale: 'No causal link in large studies.',
              evidence: [
                ClaimEvidenceView(
                  url: 'https://cdc.gov/vaccinesafety',
                  snippet: 'Studies show no association.',
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Vaccines cause autism'), findsOneWidget);
      expect(find.text('False'), findsOneWidget); // humanized verdict badge
      expect(
        find.text('No causal link in large studies.'),
        findsOneWidget,
      );
      expect(find.text('https://cdc.gov/vaccinesafety'), findsOneWidget);
    });
  });

  group('StatusPill', () {
    testWidgets('renders the label with the right state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
              body: StatusPill(label: 'Completed', state: PillState.success)),
        ),
      );
      expect(find.text('Completed'), findsOneWidget);
    });

    testWidgets('processing state shows a spinner', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
              body: StatusPill(label: 'Running', state: PillState.processing)),
        ),
      );
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('BrandMark', () {
    testWidgets('renders the logo at sidebar and hero sizes', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                BrandMark(size: 40),
                BrandMark(size: 56),
              ],
            ),
          ),
        ),
      );

      expect(find.byType(BrandMark), findsNWidgets(2));
      // The painter runs without throwing and paints a non-trivial
      // surface (the ring + wordmark are vector-drawn).
      expect(tester.takeException(), isNull);
    });
  });

  group('Themes', () {
    test('light and dark themes derive from the token palette', () {
      final light = buildLightTheme();
      final dark = buildDarkTheme();
      expect(light.brightness, Brightness.light);
      expect(dark.brightness, Brightness.dark);
      expect(light.colorScheme.primary, AppColors.primary);
      expect(dark.colorScheme.primary, AppColors.primary);
      expect(light.cardTheme, isNotNull);
    });

    test('text styles resolve readable colors in both themes', () {
      final light = buildLightTheme();
      final dark = buildDarkTheme();
      // The typography scale must never fall back to black-on-dark:
      // every style carries the scheme's on-surface color.
      expect(light.textTheme.headlineLarge?.color, light.colorScheme.onSurface);
      expect(dark.textTheme.headlineLarge?.color, dark.colorScheme.onSurface);
      expect(dark.textTheme.bodyMedium?.color, dark.colorScheme.onSurface);
      expect(
        light.textTheme.headlineLarge?.color,
        isNot(dark.textTheme.headlineLarge?.color),
      );
    });
  });
}
