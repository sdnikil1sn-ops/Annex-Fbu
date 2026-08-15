/// App button — the ANNEX action button.
///
/// Wraps Material buttons with the design-system spacing, an optional
/// leading icon, and a busy state that shows a spinner and disables the
/// action. [variant] picks the visual treatment; the default stays the
/// filled primary button.
library;

import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';

/// The visual treatment of an [AppButton].
enum AppButtonVariant { primary, secondary, outlined, danger }

/// The primary action button of the ANNEX design system.
class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    this.onPressed,
    this.icon,
    this.busy = false,
    this.expanded = false,
    this.variant = AppButtonVariant.primary,
  });

  /// The button label (a localized string — never hardcoded prose).
  final String label;

  /// Invoked when the button is tapped; null disables it.
  final VoidCallback? onPressed;

  /// Optional leading icon.
  final IconData? icon;

  /// Whether the button shows a progress spinner and ignores taps.
  final bool busy;

  /// Whether the button fills the available width.
  final bool expanded;

  /// The visual treatment.
  final AppButtonVariant variant;

  @override
  Widget build(BuildContext context) {
    final child = Row(
      mainAxisSize: expanded ? MainAxisSize.max : MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (busy)
          const SizedBox.square(
            dimension: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        else if (icon != null) ...[
          Icon(icon, size: 18),
          const SizedBox(width: AppSpacing.xs),
        ],
        if (busy && label.isNotEmpty) const SizedBox(width: AppSpacing.xs),
        Text(label),
      ],
    );

    switch (variant) {
      case AppButtonVariant.primary:
        return FilledButton(
          onPressed: busy ? null : onPressed,
          child: child,
        );
      case AppButtonVariant.secondary:
        return FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            foregroundColor: Theme.of(context).colorScheme.onPrimaryContainer,
          ),
          onPressed: busy ? null : onPressed,
          child: child,
        );
      case AppButtonVariant.outlined:
        return OutlinedButton(
          onPressed: busy ? null : onPressed,
          child: child,
        );
      case AppButtonVariant.danger:
        return FilledButton(
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.danger,
            foregroundColor: Colors.white,
          ),
          onPressed: busy ? null : onPressed,
          child: child,
        );
    }
  }
}
