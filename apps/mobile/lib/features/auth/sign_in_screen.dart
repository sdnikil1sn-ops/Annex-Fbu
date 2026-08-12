/// Sign-in screen — anonymous, Google, and email entry points.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import 'auth_controller.dart';

/// Presents the authentication options (ADR-0005).
class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.watch<AuthController>();

    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                i18n.t(StringKeys.commonLearnBeforeYouBelieve),
                style: AppTypography.displaySmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                i18n.t(StringKeys.authSignIn),
                style: AppTypography.bodyLarge,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: AppSpacing.xxl),
              AppButton(
                label: i18n.t(StringKeys.authContinueGuest),
                icon: Icons.person_outline,
                busy: controller.busy,
                expanded: true,
                onPressed: controller.signInAnonymously,
              ),
              const SizedBox(height: AppSpacing.md),
              AppButton(
                label: i18n.t(StringKeys.authContinueGoogle),
                icon: Icons.g_mobiledata,
                busy: controller.busy,
                expanded: true,
                onPressed: controller.signInWithGoogle,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
