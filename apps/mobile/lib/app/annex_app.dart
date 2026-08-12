/// ANNEX mobile app shell — theme, DI scope, and root navigation.
///
/// All features (auth, analysis, settings, i18n) come from
/// `shared_features` (Phase 12); this file contributes only the mobile
/// shell: MaterialApp wiring and the bottom-tab navigation.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

/// The root widget of the ANNEX mobile app.
class AnnexApp extends StatelessWidget {
  const AnnexApp({super.key});

  @override
  Widget build(BuildContext context) {
    final services = AppScope.of(context);
    final settings = context.watch<SettingsController>();

    return MaterialApp(
      title: 'ANNEX',
      debugShowCheckedModeBanner: false,
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      themeMode: settings.themeMode,
      home: _Root(services: services),
    );
  }
}

/// Chooses between sign-in and the main shell based on auth state.
class _Root extends StatelessWidget {
  const _Root({required this.services});

  final AppServices services;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    if (auth.user == null) {
      return const SignInScreen();
    }
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AnalysisController>(
          create: (_) => services.analysisController(),
        ),
        ChangeNotifierProvider<LessonsController>(
          create: (_) => services.lessonsController(),
        ),
      ],
      child: const _MainShell(),
    );
  }
}

/// The authenticated shell: analysis + settings tabs.
class _MainShell extends StatelessWidget {
  const _MainShell();

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        body: const TabBarView(
          children: [AnalysisScreen(), LessonsScreen(), SettingsScreen()],
        ),
        bottomNavigationBar: TabBar(
          tabs: [
            Tab(
              icon: const Icon(Icons.analytics_outlined),
              text: i18n.t(StringKeys.analysisTitle),
            ),
            Tab(
              icon: const Icon(Icons.menu_book_outlined),
              text: i18n.t(StringKeys.lessonsTitle),
            ),
            Tab(
              icon: const Icon(Icons.settings_outlined),
              text: i18n.t(StringKeys.settingsTitle),
            ),
          ],
        ),
      ),
    );
  }
}
