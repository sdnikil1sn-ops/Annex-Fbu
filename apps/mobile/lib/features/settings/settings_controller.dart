/// Settings state — active locale and brightness.
library;

import 'package:flutter/material.dart';

import '../../l10n/i18n_controller.dart';

/// Drives user-facing settings (language, theme).
class SettingsController extends ChangeNotifier {
  SettingsController({
    required this.i18n,
    ThemeMode initialThemeMode = ThemeMode.system,
  }) : _themeMode = initialThemeMode {
    i18n.addListener(_onI18nChanged);
  }

  final I18nController i18n;

  ThemeMode _themeMode;
  ThemeMode get themeMode => _themeMode;

  /// The active locale from the i18n controller.
  String get locale => i18n.locale;

  void _onI18nChanged() => notifyListeners();

  /// Set the app theme.
  void setThemeMode(ThemeMode mode) {
    _themeMode = mode;
    notifyListeners();
  }

  /// Set the active language and reload its bundle.
  Future<void> setLocale(String locale) => i18n.load(locale);

  @override
  void dispose() {
    i18n.removeListener(_onI18nChanged);
    super.dispose();
  }
}
