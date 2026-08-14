/// ANNEX web shell — theme, DI scope, and responsive navigation.
///
/// The web app shares every feature (auth, analysis, settings, i18n) with
/// the mobile app through `shared_features` (Phase 12); this shell adds
/// the browser-specific layout: a navigation rail on wide viewports and a
/// bottom navigation bar on narrow ones, so the same product adapts to
/// desktop and mobile browsers.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_features/shared_features.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

/// The root widget of the ANNEX web app.
class WebApp extends StatelessWidget {
  const WebApp({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsController>();

    return MaterialApp(
      title: 'ANNEX',
      debugShowCheckedModeBanner: false,
      theme: buildLightTheme(),
      darkTheme: buildDarkTheme(),
      themeMode: settings.themeMode,
      home: const _Root(),
    );
  }
}

/// Chooses between sign-in and the main shell based on auth state.
class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    if (auth.user == null) {
      return const SignInScreen();
    }
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AnalysisController>(
          create: (_) => AppScope.of(context).analysisController(),
        ),
        ChangeNotifierProvider<LessonsController>(
          create: (_) => AppScope.of(context).lessonsController(),
        ),
        ChangeNotifierProvider<ClassesController>(
          create: (_) => AppScope.of(context).classesController(),
        ),
        ChangeNotifierProvider<SuggestionsController>(
          create: (_) => AppScope.of(context).suggestionsController(),
        ),
      ],
      child: const WebShell(),
    );
  }
}

/// The authenticated shell: navigation rail on wide viewports, bottom
/// navigation on narrow ones.
class WebShell extends StatefulWidget {
  const WebShell({super.key});

  @override
  State<WebShell> createState() => _WebShellState();
}

class _WebShellState extends State<WebShell> {
  int _index = 0;

  static const List<Widget> _pages = [
    AnalysisScreen(),
    LessonsScreen(),
    ClassesScreen(),
    SuggestionsScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth >= 900) {
          return _WideShell(
            index: _index,
            onSelect: (index) => setState(() => _index = index),
            i18n: i18n,
          );
        }
        return _NarrowShell(
          index: _index,
          onSelect: (index) => setState(() => _index = index),
          i18n: i18n,
        );
      },
    );
  }
}

/// Desktop/tablet layout: persistent navigation rail.
class _WideShell extends StatelessWidget {
  const _WideShell({
    required this.index,
    required this.onSelect,
    required this.i18n,
  });

  final int index;
  final ValueChanged<int> onSelect;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: index,
            onDestinationSelected: onSelect,
            labelType: NavigationRailLabelType.all,
            destinations: [
              NavigationRailDestination(
                icon: const Icon(Icons.analytics_outlined),
                selectedIcon: const Icon(Icons.analytics),
                label: Text(i18n.t(StringKeys.analysisTitle)),
              ),
              NavigationRailDestination(
                icon: const Icon(Icons.menu_book_outlined),
                selectedIcon: const Icon(Icons.menu_book),
                label: Text(i18n.t(StringKeys.lessonsTitle)),
              ),
              NavigationRailDestination(
                icon: const Icon(Icons.school_outlined),
                selectedIcon: const Icon(Icons.school),
                label: Text(i18n.t(StringKeys.classesTitle)),
              ),
              NavigationRailDestination(
                icon: const Icon(Icons.translate_outlined),
                selectedIcon: const Icon(Icons.translate),
                label: Text(i18n.t(StringKeys.suggestionsTitle)),
              ),
              NavigationRailDestination(
                icon: const Icon(Icons.settings_outlined),
                selectedIcon: const Icon(Icons.settings),
                label: Text(i18n.t(StringKeys.settingsTitle)),
              ),
            ],
          ),
          const VerticalDivider(width: 1),
          Expanded(
            child: IndexedStack(index: index, children: _WebShellState._pages),
          ),
        ],
      ),
    );
  }
}

/// Phone layout: bottom navigation bar.
class _NarrowShell extends StatelessWidget {
  const _NarrowShell({
    required this.index,
    required this.onSelect,
    required this.i18n,
  });

  final int index;
  final ValueChanged<int> onSelect;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: index, children: _WebShellState._pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: onSelect,
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.analytics_outlined),
            selectedIcon: const Icon(Icons.analytics),
            label: i18n.t(StringKeys.analysisTitle),
          ),
          NavigationDestination(
            icon: const Icon(Icons.menu_book_outlined),
            selectedIcon: const Icon(Icons.menu_book),
            label: i18n.t(StringKeys.lessonsTitle),
          ),
          NavigationDestination(
            icon: const Icon(Icons.school_outlined),
            selectedIcon: const Icon(Icons.school),
            label: i18n.t(StringKeys.classesTitle),
          ),
          NavigationDestination(
            icon: const Icon(Icons.translate_outlined),
            selectedIcon: const Icon(Icons.translate),
            label: i18n.t(StringKeys.suggestionsTitle),
          ),
          NavigationDestination(
            icon: const Icon(Icons.settings_outlined),
            selectedIcon: const Icon(Icons.settings),
            label: i18n.t(StringKeys.settingsTitle),
          ),
        ],
      ),
    );
  }
}
