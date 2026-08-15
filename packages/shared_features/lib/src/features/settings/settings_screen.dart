/// Settings screen — language, theme, and account actions.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import '../auth/auth_controller.dart';
import 'settings_controller.dart';

/// Preferences: language, theme, account.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final settings = context.watch<SettingsController>();
    final auth = context.watch<AuthController>();

    return Scaffold(
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        children: [
          PageHeader(
            icon: Icons.settings_outlined,
            title: i18n.t(StringKeys.settingsTitle),
            subtitle: i18n.t(StringKeys.settingsSubtitle),
          ),
          const SizedBox(height: AppSpacing.lg),
          _LanguageSection(settings: settings, i18n: i18n),
          const SizedBox(height: AppSpacing.md),
          _ThemeSection(settings: settings, i18n: i18n),
          const SizedBox(height: AppSpacing.md),
          _AccountSection(auth: auth, i18n: i18n),
          const SizedBox(height: AppSpacing.md),
        ],
      ),
    );
  }
}

class _LanguageSection extends StatelessWidget {
  const _LanguageSection({required this.settings, required this.i18n});

  final SettingsController settings;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final locales = i18n.locales ?? const <LocaleInfo>[];
    final current = settings.locale;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              i18n.t(StringKeys.settingsLanguage),
              style: AppTypography.titleMedium,
            ),
            const SizedBox(height: AppSpacing.sm),
            RadioGroup<String>(
              groupValue: current,
              onChanged: (value) {
                if (value != null) settings.setLocale(value);
              },
              child: Column(
                children: [
                  for (final locale in locales)
                    RadioListTile<String>(
                      title: Text(_displayName(locale.code)),
                      value: locale.code,
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _displayName(String code) {
    const names = {
      'ar': 'العربية',
      'de': 'Deutsch',
      'en': 'English',
      'es': 'Español',
      'fr': 'Français',
      'ja': '日本語',
      'pt': 'Português',
    };
    return names[code] ?? code;
  }
}

class _ThemeSection extends StatelessWidget {
  const _ThemeSection({required this.settings, required this.i18n});

  final SettingsController settings;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              i18n.t(StringKeys.settingsTheme),
              style: AppTypography.titleMedium,
            ),
            const SizedBox(height: AppSpacing.sm),
            SegmentedButton<ThemeMode>(
              segments: [
                ButtonSegment(
                  value: ThemeMode.system,
                  label: Text(i18n.t(StringKeys.settingsThemeSystem)),
                ),
                ButtonSegment(
                  value: ThemeMode.light,
                  label: Text(i18n.t(StringKeys.settingsThemeLight)),
                ),
                ButtonSegment(
                  value: ThemeMode.dark,
                  label: Text(i18n.t(StringKeys.settingsThemeDark)),
                ),
              ],
              selected: {settings.themeMode},
              onSelectionChanged: (selection) =>
                  settings.setThemeMode(selection.first),
            ),
          ],
        ),
      ),
    );
  }
}

class _AccountSection extends StatelessWidget {
  const _AccountSection({required this.auth, required this.i18n});

  final AuthController auth;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final user = auth.user;
    final email = user?.email;
    final name = user?.displayName ??
        (email == null || email.isEmpty ? 'A' : email.split('@').first);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              i18n.t(StringKeys.settingsAccount),
              style: AppTypography.titleMedium,
            ),
            const SizedBox(height: AppSpacing.sm),
            if (user != null)
              Row(
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: AppColors.primaryContainer,
                    child: Text(
                      name.characters.first.toUpperCase(),
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 18,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(name, style: AppTypography.titleMedium),
                        if (email != null && email.isNotEmpty)
                          Text(
                            email,
                            style: AppTypography.bodyMedium.copyWith(
                              color: Theme.of(
                                context,
                              ).colorScheme.onSurfaceVariant,
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            const SizedBox(height: AppSpacing.md),
            AppButton(
              label: i18n.t(StringKeys.authSignOut),
              icon: Icons.logout,
              variant: AppButtonVariant.outlined,
              busy: auth.busy,
              onPressed: auth.user == null ? null : auth.signOut,
            ),
          ],
        ),
      ),
    );
  }
}
