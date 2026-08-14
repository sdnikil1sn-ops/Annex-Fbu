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

    // The completion button sits below the fold on small viewports. The
    // mobile shell's scrollable TabBar adds extra Scrollables, so scope
    // the search to the lessons screen.
    final lessonsScrollable = find.descendant(
      of: find.byType(LessonsScreen),
      matching: find.byType(Scrollable),
    );
    await tester.scrollUntilVisible(
      find.text('Mark complete'),
      100,
      scrollable: lessonsScrollable,
    );
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

  testWidgets('suggestions tab proposes a translation for the locale', (
    tester,
  ) async {
    final services = _buildServices();
    // The mock serves untranslated keys only for pt; the default locale
    // (en) is complete by definition.
    final i18n = I18nController(api: services.api, locale: 'pt');
    final settings = SettingsController(i18n: i18n);
    final servicesPt = AppServices(
      api: services.api,
      authController: services.authController,
      i18n: i18n,
      settings: settings,
    );
    addTearDown(services.authController.dispose);
    addTearDown(i18n.dispose);
    addTearDown(settings.dispose);
    await i18n.load();
    await servicesPt.authController.signInAnonymously();

    await tester.pumpWidget(_wrap(servicesPt));
    await tester.pumpAndSettle();

    // Switch to the Contribute tab and browse the missing keys.
    await tester.tap(find.text('Contribuir'));
    await tester.pumpAndSettle();
    expect(find.text('common.retry'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);

    // Propose a translation and verify it lands in the submissions list.
    await tester.tap(find.text('Propor tradução').first);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Tentar novamente');
    await tester.tap(find.text('Propor tradução').last);
    await tester.pumpAndSettle();

    expect(find.text('Tentar novamente'), findsWidgets);
    expect(find.text('Em análise'), findsOneWidget);
  });

  testWidgets('sources tab searches and rates a source', (tester) async {
    final services = _buildServices();
    addTearDown(services.authController.dispose);
    addTearDown(services.i18n.dispose);
    addTearDown(services.settings.dispose);
    await services.i18n.load();
    await services.authController.signInAnonymously();

    await tester.pumpWidget(_wrap(services));
    await tester.pumpAndSettle();

    // Switch to the Sources tab and search the seeded registry.
    await tester.tap(find.text('Sources'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'snopes');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();
    expect(find.text('Snopes'), findsOneWidget);

    // Open the profile: the model score and community signal render.
    await tester.tap(find.text('Snopes'));
    await tester.pumpAndSettle();
    expect(find.text('snopes.com'), findsOneWidget);
    expect(find.text('Model score'), findsOneWidget);

    // Rate the source and verify the caller's rating appears.
    await tester.tap(find.byIcon(Icons.star_border).first);
    await tester.pumpAndSettle();
    expect(find.text('Your rating'), findsOneWidget);
    expect(find.byIcon(Icons.star), findsWidgets);
  });

  testWidgets('moderators see and clear the translation review queue', (
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

    // The mock profile is a moderator, so the Contribute tab shows the
    // review queue with two seeded pending suggestions.
    await tester.tap(find.text('Contribute'));
    await tester.pumpAndSettle();
    expect(find.text('Review queue'), findsOneWidget);
    expect(find.text('lessons.complete'), findsOneWidget);
    expect(find.text('common.retry'), findsOneWidget);

    // Approve one suggestion; it leaves the queue.
    await tester.tap(find.byIcon(Icons.check_circle_outline).first);
    await tester.pumpAndSettle();
    expect(find.text('lessons.complete'), findsNothing);
    expect(find.text('common.retry'), findsOneWidget);
  });
}
