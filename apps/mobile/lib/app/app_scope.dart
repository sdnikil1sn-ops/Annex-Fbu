/// Composition root — holds the app's services for inherited lookup.
///
/// Built once in `main()` (or by tests with mocks injected); widgets
/// resolve services through [AppScope.of]. This keeps dependencies
/// explicit and injectable (ADR-0003) without a service locator.
library;

import 'package:flutter/widgets.dart';

import '../core/api/analysis_api.dart';
import '../features/auth/auth_controller.dart';
import '../features/analysis/analysis_controller.dart';
import '../features/settings/settings_controller.dart';
import '../l10n/i18n_controller.dart';

/// The services wired at the composition root.
class AppServices {
  const AppServices({
    required this.api,
    required this.authController,
    required this.i18n,
    required this.settings,
  });

  final AnalysisApi api;
  final AuthController authController;
  final I18nController i18n;
  final SettingsController settings;

  /// A fresh analysis controller bound to the app's API.
  AnalysisController analysisController() => AnalysisController(api: api);
}

/// Inherited widget exposing [AppServices] to the widget tree.
class AppScope extends InheritedWidget {
  const AppScope({super.key, required this.services, required super.child});

  final AppServices services;

  /// Resolve the app services from context.
  ///
  /// Uses a non-dependent lookup because [AppScope] is built once at the
  /// composition root and never changes; this keeps it safe to call from
  /// both build methods and callbacks.
  static AppServices of(BuildContext context) {
    final scope = context.getInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope is missing from the widget tree');
    return scope!.services;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) => services != oldWidget.services;
}
