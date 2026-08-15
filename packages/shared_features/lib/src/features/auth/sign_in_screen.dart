/// Sign-in screen — email/password and Google entry points.
///
/// A split hero: the brand story ("Learn before you believe.") on one
/// side, the sign-in card on the other. The card offers sign-in and
/// account creation (tabs) plus a Google button; no anonymous access.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import 'auth_controller.dart';

/// Presents the authentication options (ADR-0005).
class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth >= 960) {
            return const _SplitLayout();
          }
          return const _StackedLayout();
        },
      ),
    );
  }
}

/// Wide layout: brand panel left, sign-in card right.
class _SplitLayout extends StatelessWidget {
  const _SplitLayout();

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    return Row(
      children: [
        Expanded(
          flex: 11,
          child: _BrandPanel(i18n: i18n),
        ),
        Expanded(
          flex: 9,
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.xxl,
                vertical: AppSpacing.xl,
              ),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _SignInCard(i18n: i18n),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Narrow layout: brand block above the card.
class _StackedLayout extends StatelessWidget {
  const _StackedLayout();

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const _CompactBrand(),
          const SizedBox(height: AppSpacing.xl),
          _SignInCard(i18n: i18n),
        ],
      ),
    );
  }
}

/// The dark gradient brand panel (wide layout).
class _BrandPanel extends StatelessWidget {
  const _BrandPanel({required this.i18n});

  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color(0xFF1A1240),
            Color(0xFF2A1B66),
            Color(0xFF3B2E8A),
          ],
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xxl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const BrandMark(size: 56),
              const SizedBox(height: AppSpacing.xl),
              Text(
                i18n.t(StringKeys.commonLearnBeforeYouBelieve),
                style: const TextStyle(
                  fontSize: 44,
                  height: 1.15,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -1,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                i18n.t(StringKeys.commonAppTagline),
                style: const TextStyle(
                  fontSize: 17,
                  height: 1.5,
                  fontWeight: FontWeight.w400,
                  color: Color(0xFFC9C1F2),
                ),
              ),
              const SizedBox(height: AppSpacing.xl),
              _FeatureRow(
                icon: Icons.analytics_outlined,
                label: i18n.t(StringKeys.authFeatureAnalyze),
              ),
              const SizedBox(height: AppSpacing.md),
              _FeatureRow(
                icon: Icons.public_outlined,
                label: i18n.t(StringKeys.authFeatureSources),
              ),
              const SizedBox(height: AppSpacing.md),
              _FeatureRow(
                icon: Icons.menu_book_outlined,
                label: i18n.t(StringKeys.authFeatureLessons),
              ),
              const Spacer(),
              Text(
                i18n.t(StringKeys.commonOpenSourceNote),
                style: const TextStyle(
                  fontSize: 12.5,
                  color: Color(0xFF8E86C4),
                  letterSpacing: 0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// One feature bullet on the brand panel.
class _FeatureRow extends StatelessWidget {
  const _FeatureRow({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 38,
          height: 38,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.14),
            ),
          ),
          child: Icon(icon, size: 20, color: const Color(0xFF7DF3DC)),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.w500,
              color: Color(0xFFEAE6FA),
            ),
          ),
        ),
      ],
    );
  }
}

/// Compact brand block for narrow screens.
class _CompactBrand extends StatelessWidget {
  const _CompactBrand();

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const BrandMark(size: 48),
          const SizedBox(height: AppSpacing.lg),
          Text(
            i18n.t(StringKeys.commonLearnBeforeYouBelieve),
            style: AppTypography.displaySmall,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            i18n.t(StringKeys.commonAppTagline),
            style: AppTypography.bodyLarge.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

/// The sign-in card: tabs for sign-in / create account, email+password
/// form, and a Google button.
class _SignInCard extends StatefulWidget {
  const _SignInCard({required this.i18n});

  final I18nController i18n;

  @override
  State<_SignInCard> createState() => _SignInCardState();
}

class _SignInCardState extends State<_SignInCard> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _creatingAccount = false;
  bool _obscure = true;

  I18nController get i18n => widget.i18n;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = context.watch<AuthController>();
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              i18n.t(
                _creatingAccount ? StringKeys.authSignUp : StringKeys.authSignIn,
              ),
              style: AppTypography.headlineMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            SegmentedButton<bool>(
              segments: [
                ButtonSegment(
                  value: false,
                  label: Text(i18n.t(StringKeys.authSignInTab)),
                ),
                ButtonSegment(
                  value: true,
                  label: Text(i18n.t(StringKeys.authCreateAccount)),
                ),
              ],
              selected: {_creatingAccount},
              onSelectionChanged: (selection) {
                setState(() => _creatingAccount = selection.first);
                controller.clearError();
              },
            ),
            const SizedBox(height: AppSpacing.lg),
            Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  TextFormField(
                    controller: _email,
                    enabled: !controller.busy,
                    keyboardType: TextInputType.emailAddress,
                    autocorrect: false,
                    textInputAction: TextInputAction.next,
                    decoration: InputDecoration(
                      labelText: i18n.t(StringKeys.authEmail),
                      prefixIcon: const Icon(Icons.mail_outline_rounded),
                    ),
                    validator: (value) => _validateEmail(value, i18n),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  TextFormField(
                    controller: _password,
                    enabled: !controller.busy,
                    obscureText: _obscure,
                    textInputAction: TextInputAction.next,
                    decoration: InputDecoration(
                      labelText: i18n.t(StringKeys.authPassword),
                      prefixIcon: const Icon(Icons.lock_outline_rounded),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscure
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                        onPressed: () =>
                            setState(() => _obscure = !_obscure),
                      ),
                    ),
                    validator: (value) => _validatePassword(value, i18n),
                  ),
                  if (_creatingAccount) ...[
                    const SizedBox(height: AppSpacing.sm),
                    TextFormField(
                      controller: _confirm,
                      enabled: !controller.busy,
                      obscureText: _obscure,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(controller),
                      decoration: InputDecoration(
                        labelText: i18n.t(StringKeys.authConfirmPassword),
                        prefixIcon: const Icon(Icons.lock_outline_rounded),
                      ),
                      validator: (value) => _validateConfirm(value, i18n),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.lg),
            AppButton(
              label: i18n.t(
                _creatingAccount
                    ? StringKeys.authCreateAccount
                    : StringKeys.authSignIn,
              ),
              icon: _creatingAccount
                  ? Icons.person_add_alt_1_rounded
                  : Icons.login_rounded,
              busy: controller.busy,
              expanded: true,
              onPressed: () => _submit(controller),
            ),
            const SizedBox(height: AppSpacing.sm),
            _GoogleButton(
              label: i18n.t(StringKeys.authContinueGoogle),
              busy: controller.busy,
              onPressed: controller.signInWithGoogle,
            ),
            if (controller.error != null) ...[
              const SizedBox(height: AppSpacing.sm),
              Text(
                _friendlyError(controller, i18n),
                style: AppTypography.bodySmall.copyWith(
                  color: colorScheme.error,
                ),
                textAlign: TextAlign.center,
              ),
            ],
            const SizedBox(height: AppSpacing.lg),
            Divider(color: colorScheme.outline.withValues(alpha: 0.5)),
            const SizedBox(height: AppSpacing.md),
            Row(
              children: [
                Icon(
                  Icons.lock_outline_rounded,
                  size: 16,
                  color: colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: AppSpacing.xs),
                Expanded(
                  child: Text(
                    i18n.t(StringKeys.authPrivacyNote),
                    style: AppTypography.bodySmall.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit(AuthController controller) async {
    if (!_formKey.currentState!.validate()) return;
    final email = _email.text.trim();
    final password = _password.text;
    if (_creatingAccount) {
      await controller.createAccountWithEmail(email, password);
    } else {
      await controller.signInWithEmail(email, password);
    }
  }

  /// Map a Firebase error code to a friendly, translated message.
  static String _friendlyError(AuthController controller, I18nController i18n) {
    final key = switch (controller.errorCode) {
      'wrong-password' || 'invalid-credential' =>
        StringKeys.authErrorWrongPassword,
      'user-not-found' => StringKeys.authErrorUserNotFound,
      'email-already-in-use' => StringKeys.authErrorEmailInUse,
      'weak-password' => StringKeys.authErrorWeakPassword,
      'too-many-requests' => StringKeys.authErrorTooManyRequests,
      'network-request-failed' => StringKeys.authErrorNetwork,
      _ => StringKeys.authErrorDefault,
    };
    return i18n.t(key);
  }

  static String? _validateEmail(String? value, I18nController i18n) {
    final email = value?.trim() ?? '';
    final ok = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email);
    if (email.isEmpty || !ok) return i18n.t(StringKeys.authInvalidEmail);
    return null;
  }

  static String? _validatePassword(String? value, I18nController i18n) {
    final password = value ?? '';
    if (password.isEmpty) return i18n.t(StringKeys.authPasswordTooShort);
    if (password.length < 8) return i18n.t(StringKeys.authPasswordTooShort);
    final hasLetter = RegExp(r'[A-Za-z]').hasMatch(password);
    final hasNumber = RegExp(r'[0-9]').hasMatch(password);
    if (!hasLetter || !hasNumber) return i18n.t(StringKeys.authPasswordTooWeak);
    return null;
  }

  String? _validateConfirm(String? value, I18nController i18n) {
    if (value != _password.text) {
      return i18n.t(StringKeys.authPasswordsDontMatch);
    }
    return null;
  }
}

/// The Google sign-in button (white outline with the G mark).
class _GoogleButton extends StatelessWidget {
  const _GoogleButton({
    required this.label,
    required this.busy,
    required this.onPressed,
  });

  final String label;
  final bool busy;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return OutlinedButton(
      onPressed: busy ? null : onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: colorScheme.onSurface,
        side: BorderSide(color: colorScheme.outline),
        backgroundColor: colorScheme.surface,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (busy)
            const SizedBox.square(
              dimension: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            const Text(
              'G',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: Color(0xFF4285F4),
                height: 1,
              ),
            ),
          const SizedBox(width: AppSpacing.sm),
          Text(label),
        ],
      ),
    );
  }
}
