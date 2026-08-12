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
}
