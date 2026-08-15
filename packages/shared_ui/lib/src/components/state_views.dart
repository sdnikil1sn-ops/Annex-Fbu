/// Empty and error state views.
///
/// Replaces ad-hoc "pill + retry button" columns with a consistent,
/// friendly state block: an icon in a soft circle, a title, an optional
/// message, and an optional action button.
library;

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// The primary action of a state view.
class StateAction {
  const StateAction({required this.label, required this.onPressed, this.icon});

  final String label;
  final VoidCallback onPressed;
  final IconData? icon;
}

/// A friendly error state with an optional retry action.
class AppErrorState extends StatelessWidget {
  const AppErrorState({
    super.key,
    this.title = 'Something went wrong',
    this.message,
    this.action,
    this.icon = Icons.cloud_off_outlined,
  });

  final String title;
  final String? message;
  final StateAction? action;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: _StateView(
          icon: icon,
          iconColor: AppColors.danger,
          title: title,
          message: message,
          action: action,
        ),
      ),
    );
  }
}

/// A calm empty state with an optional primary action.
class AppEmptyState extends StatelessWidget {
  const AppEmptyState({
    super.key,
    this.title = 'Nothing here yet',
    this.message,
    this.action,
    this.icon = Icons.inbox_outlined,
  });

  final String title;
  final String? message;
  final StateAction? action;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: _StateView(
          icon: icon,
          iconColor: Theme.of(context).colorScheme.onSurfaceVariant,
          title: title,
          message: message,
          action: action,
        ),
      ),
    );
  }
}

/// The shared layout for [AppErrorState] and [AppEmptyState].
class _StateView extends StatelessWidget {
  const _StateView({
    required this.icon,
    required this.iconColor,
    required this.title,
    this.message,
    this.action,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String? message;
  final StateAction? action;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: iconColor.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 34, color: iconColor),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text(
          title,
          style: AppTypography.titleLarge,
          textAlign: TextAlign.center,
        ),
        if (message != null && message!.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.xs),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Text(
              message!,
              style: AppTypography.bodyMedium.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ],
        if (action != null) ...[
          const SizedBox(height: AppSpacing.lg),
          FilledButton.icon(
            onPressed: action!.onPressed,
            icon: Icon(action!.icon ?? Icons.refresh, size: 18),
            label: Text(action!.label),
          ),
        ],
      ],
    );
  }
}
