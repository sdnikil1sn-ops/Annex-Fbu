import 'package:annex_web/app/web_shell.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_ui/shared_ui.dart';

AppServices _buildServices({AuthController? auth}) {
  final api = MockAnalysisApi(delay: Duration.zero);
  final gateway = MockAuthGateway();
  final authController = auth ?? AuthController(gateway);
  final i18n = I18nController(api: api, locale: 'en');
  final settings = SettingsController(i18n: i18n);
  return AppServices(
    api: api,
    authController: authController,
    i18n: i18n,
    settings: settings,
  );
}

Widget _wrap(AppServices services) {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider.value(value: services.authController),
      ChangeNotifierProvider.value(value: services.i18n),
      ChangeNotifierProvider.value(value: services.settings),
    ],
    child: AppScope(services: services, child: const WebApp()),
  );
}

void main() {
  testWidgets('signed-out users see the sign-in screen', (tester) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();

    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    expect(find.text('Learn before you believe.'), findsOneWidget);
  });

  testWidgets('wide viewport shows the navigation rail after sign-in', (
    tester,
  ) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();
    await services.authController.signInAnonymously();

    await tester.binding.setSurfaceSize(const Size(1200, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    // Desktop layout: a rail is present, and the analysis input is visible.
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Analyze text'), findsOneWidget);
  });

  testWidgets('narrow viewport shows the bottom navigation bar', (
    tester,
  ) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();
    await services.authController.signInAnonymously();

    await tester.binding.setSurfaceSize(const Size(480, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
  });

  testWidgets('full flow: submit text and render the report', (tester) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();
    await services.authController.signInAnonymously();

    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'The Earth orbits the Sun');
    await tester.tap(find.text('Analyze text'));
    await tester.pumpAndSettle();

    // The mock completes instantly; the report shows the summary and claims.
    expect(find.textContaining('two checkable claims'), findsOneWidget);
    expect(find.text('The claim cites an outdated study'), findsOneWidget);
    expect(find.byType(ScoreMeter), findsOneWidget);
  });

  testWidgets('lessons tab lists the curriculum and completes a lesson', (
    tester,
  ) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();
    await services.authController.signInAnonymously();

    await tester.binding.setSurfaceSize(const Size(480, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    // The curriculum is prefetched; the mock serves two seeded lessons.
    await tester.tap(find.text('Lessons'));
    await tester.pumpAndSettle();
    expect(find.text('Spotting Misinformation'), findsOneWidget);
    expect(find.text('Understanding Credibility Scores'), findsOneWidget);

    // Open the first lesson and complete it.
    await tester.tap(find.text('Spotting Misinformation'));
    await tester.pumpAndSettle();
    expect(find.text('Why misinformation spreads'), findsOneWidget);

    // The completion button sits below the fold on narrow viewports. The
    // web shell's IndexedStack keeps every page's scrollable alive, so
    // scope the search to the lessons screen, then scroll past the bottom
    // navigation bar so the button is fully tappable.
    final lessonsScrollable = find.descendant(
      of: find.byType(LessonsScreen),
      matching: find.byType(Scrollable),
    );
    await tester.scrollUntilVisible(
      find.text('Mark complete'),
      100,
      scrollable: lessonsScrollable,
    );
    await tester.drag(lessonsScrollable, const Offset(0, -120));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mark complete'));
    await tester.pumpAndSettle();
    expect(find.text('Completed'), findsWidgets);
  });

  testWidgets('classes tab lists classes and shows the seeded invite code', (
    tester,
  ) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();
    await services.authController.signInAnonymously();

    await tester.binding.setSurfaceSize(const Size(480, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    // Switch to the Classes tab; the mock seeds one class.
    await tester.tap(find.text('Classes'));
    await tester.pumpAndSettle();
    expect(find.text('Media Literacy 101'), findsOneWidget);
    expect(find.textContaining('ANNEX234'), findsOneWidget);

    // Open the class and verify the roster renders.
    await tester.tap(find.text('Media Literacy 101'));
    await tester.pumpAndSettle();
    expect(find.text('Ms. Alvarez'), findsOneWidget);
    expect(find.text('Student One'), findsOneWidget);
  });
}
