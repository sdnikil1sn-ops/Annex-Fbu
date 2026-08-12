import 'package:annex_mobile/app/annex_app.dart';
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
    child: AppScope(services: services, child: const AnnexApp()),
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

  testWidgets('signing in shows the analysis shell', (tester) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();

    await services.authController.signInAnonymously();
    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Analyze text'), findsOneWidget);
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

    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    // Switch to the Lessons tab and browse the seeded curriculum.
    await tester.tap(find.text('Lessons'));
    await tester.pumpAndSettle();
    expect(find.text('Spotting Misinformation'), findsOneWidget);

    // Open the first lesson and complete it.
    await tester.tap(find.text('Spotting Misinformation'));
    await tester.pumpAndSettle();
    expect(find.text('Why misinformation spreads'), findsOneWidget);

    // The completion button sits below the fold on small viewports.
    await tester.scrollUntilVisible(
      find.text('Mark complete'),
      100,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.text('Mark complete'));
    await tester.pumpAndSettle();
    expect(find.text('Completed'), findsWidgets);
  });
}
