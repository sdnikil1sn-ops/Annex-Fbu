/// ANNEX web shell — theme, DI scope, and responsive navigation.
///
/// The web app shares every feature (auth, analysis, settings, i18n) with
/// the mobile app through `shared_features` (Phase 12); this shell adds
/// the browser-specific layout: a branded dark sidebar on wide viewports
/// and a bottom navigation bar on narrow ones. Content pages are capped
/// at a readable width so desktop screens stay composed.
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
        ChangeNotifierProvider<SourcesController>(
          create: (_) => AppScope.of(context).sourcesController(),
        ),
      ],
      child: const WebShell(),
    );
  }
}

/// The authenticated shell: branded sidebar on wide viewports, bottom
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
    SourcesScreen(),
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

/// The rail destinations (sidebar).
List<NavigationRailDestination> _railDestinations(I18nController i18n) {
  return [
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
      icon: const Icon(Icons.public_outlined),
      selectedIcon: const Icon(Icons.public),
      label: Text(i18n.t(StringKeys.sourcesTitle)),
    ),
    NavigationRailDestination(
      icon: const Icon(Icons.settings_outlined),
      selectedIcon: const Icon(Icons.settings),
      label: Text(i18n.t(StringKeys.settingsTitle)),
    ),
  ];
}

/// The bottom-navigation destinations (narrow layouts).
List<NavigationDestination> _barDestinations(I18nController i18n) {
  return [
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
      icon: const Icon(Icons.public_outlined),
      selectedIcon: const Icon(Icons.public),
      label: i18n.t(StringKeys.sourcesTitle),
    ),
    NavigationDestination(
      icon: const Icon(Icons.settings_outlined),
      selectedIcon: const Icon(Icons.settings),
      label: i18n.t(StringKeys.settingsTitle),
    ),
  ];
}

/// Desktop layout: a branded dark sidebar with a user footer.
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
          _Sidebar(index: index, onSelect: onSelect, i18n: i18n),
          Expanded(
            child: ColoredBox(
              color: Theme.of(context).scaffoldBackgroundColor,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: AppSpacing.pageMaxWidth,
                  ),
                  child: IndexedStack(
                    index: index,
                    children: _WebShellState._pages,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// The branded navigation rail with a user footer.
class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.index,
    required this.onSelect,
    required this.i18n,
  });

  final int index;
  final ValueChanged<int> onSelect;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 236,
      decoration: const BoxDecoration(
        color: AppColors.sidebarBackground,
        border: Border(
          right: BorderSide(color: Color(0xFF262139), width: 1),
        ),
      ),
      child: NavigationRail(
        selectedIndex: index,
        onDestinationSelected: onSelect,
        labelType: NavigationRailLabelType.all,
        minExtendedWidth: 236,
        groupAlignment: 0,
        leading: _SidebarBrand(i18n: i18n),
        trailing: const _SidebarUser(),
        destinations: _railDestinations(i18n),
      ),
    );
  }
}

/// The ANNEX brand block at the top of the sidebar.
class _SidebarBrand extends StatelessWidget {
  const _SidebarBrand({required this.i18n});

  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 22),
      child: Row(
        children: [
          const BrandMark(size: 40),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'ANNEX',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.5,
                    color: AppColors.onSidebar,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  i18n.t(StringKeys.commonLearnBeforeYouBelieve),
                  style: const TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w500,
                    letterSpacing: 0.2,
                    color: AppColors.onSidebarMuted,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// The signed-in user card at the bottom of the sidebar.
class _SidebarUser extends StatelessWidget {
  const _SidebarUser();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final i18n = AppScope.of(context).i18n;
    final user = auth.user;
    final email = user?.email;
    final name = user?.displayName ??
        (email == null || email.isEmpty
            ? 'A'
            : email.split('@').first);
    final detail = email ?? '';

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 16),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: AppColors.gradientStart,
            child: Text(
              name.isEmpty ? 'A' : name.characters.first.toUpperCase(),
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                fontSize: 14,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  name,
                  style: const TextStyle(
                    color: AppColors.onSidebar,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  detail,
                  style: const TextStyle(
                    color: AppColors.onSidebarMuted,
                    fontSize: 11,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            tooltip: i18n.t(StringKeys.authSignOut),
            onPressed: auth.busy ? null : auth.signOut,
            icon: const Icon(Icons.logout_rounded, size: 19),
            color: AppColors.onSidebarMuted,
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
        destinations: _barDestinations(i18n),
      ),
    );
  }
}
