/// Translation contribution screen — community translations (Phase 18/21).
///
/// Lists the untranslated keys for the active locale, lets contributors
/// propose translations (submitted for moderator review), and shows their
/// own submissions with status. All strings resolve through the typed
/// [StringKeys] registry.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import 'suggestions_controller.dart';

/// The community translation UI.
class SuggestionsScreen extends StatefulWidget {
  const SuggestionsScreen({super.key});

  @override
  State<SuggestionsScreen> createState() => _SuggestionsScreenState();
}

class _SuggestionsScreenState extends State<SuggestionsScreen> {
  I18nController? _i18n;

  @override
  void initState() {
    super.initState();
    // Prefetch the missing keys once per app instance (the shells build
    // all pages eagerly via IndexedStack, so the first notifyListeners
    // must not run during build). Reloads follow a locale change.
    final controller = context.read<SuggestionsController>();
    _i18n = AppScope.of(context).i18n;
    if (!controller.hasLoaded) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) controller.load(_i18n!.locale);
      });
    }
    _i18n!.addListener(_onLocaleChanged);
  }

  @override
  void dispose() {
    _i18n?.removeListener(_onLocaleChanged);
    super.dispose();
  }

  void _onLocaleChanged() {
    final controller = context.read<SuggestionsController>();
    if (controller.hasLoaded) {
      controller.load(_i18n!.locale);
    }
  }

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.watch<SuggestionsController>();

    return Scaffold(
      appBar: AppBar(title: Text(i18n.t(StringKeys.suggestionsTitle))),
      body: _buildBody(context, i18n, controller),
    );
  }

  Widget _buildBody(
    BuildContext context,
    I18nController i18n,
    SuggestionsController controller,
  ) {
    if (controller.state == SuggestionsFlowState.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (controller.state == SuggestionsFlowState.failed) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            StatusPill(
              label: i18n.t(StringKeys.suggestionsError),
              state: PillState.failure,
            ),
            const SizedBox(height: AppSpacing.md),
            AppButton(
              label: i18n.t(StringKeys.commonRetry),
              icon: Icons.refresh,
              onPressed: () => controller.load(i18n.locale),
            ),
          ],
        ),
      );
    }
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        Text(
          i18n
              .t(StringKeys.suggestionsContributorNote)
              .replaceFirst('{locale}', i18n.locale),
          style: AppTypography.bodyMedium,
        ),
        const SizedBox(height: AppSpacing.lg),

        // Untranslated keys for the active locale.
        Text(
          i18n.t(StringKeys.suggestionsMissing),
          style: AppTypography.titleMedium,
        ),
        const SizedBox(height: AppSpacing.xs),
        if (controller.missing.isEmpty)
          StatusPill(label: i18n.t(StringKeys.suggestionsEmpty))
        else
          for (final key in controller.missing) ...[
            _MissingKeyCard(
              missingKey: key,
              i18n: i18n,
              busy: controller.busy,
              onPropose: () => _showProposeDialog(context, key),
            ),
            const SizedBox(height: AppSpacing.xs),
          ],
        const SizedBox(height: AppSpacing.lg),

        // The caller's submissions with review status.
        Text(
          i18n.t(StringKeys.suggestionsYourSubmissions),
          style: AppTypography.titleMedium,
        ),
        const SizedBox(height: AppSpacing.xs),
        if (controller.submissions.isEmpty)
          StatusPill(label: i18n.t(StringKeys.suggestionsNoSubmissions))
        else
          for (final suggestion in controller.submissions) ...[
            _SubmissionCard(suggestion: suggestion, i18n: i18n),
            const SizedBox(height: AppSpacing.xs),
          ],
        const SizedBox(height: AppSpacing.md),
      ],
    );
  }

  void _showProposeDialog(BuildContext context, MissingKey key) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.read<SuggestionsController>();
    final valueController = TextEditingController();
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(i18n.t(StringKeys.suggestionsPropose)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(key.fullKey, style: AppTypography.labelMedium),
            const SizedBox(height: AppSpacing.xs),
            Text(
              '${i18n.t(StringKeys.suggestionsEnglish)}: ${key.englishValue}',
              style: AppTypography.bodyMedium,
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              controller: valueController,
              autofocus: true,
              maxLines: 2,
              decoration: InputDecoration(
                labelText: i18n.t(StringKeys.suggestionsValue),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(i18n.t(StringKeys.commonCancel)),
          ),
          FilledButton(
            onPressed: () async {
              final value = valueController.text.trim();
              if (value.isEmpty) return;
              final ok = await controller.submit(
                locale: i18n.locale,
                key: key,
                value: value,
              );
              if (dialogContext.mounted) {
                Navigator.of(dialogContext).pop();
                if (ok) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(i18n.t(StringKeys.suggestionsSubmitted)),
                    ),
                  );
                } else if (controller.error != null) {
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(SnackBar(content: Text(controller.error!)));
                }
              }
            },
            child: Text(i18n.t(StringKeys.suggestionsPropose)),
          ),
        ],
      ),
    );
  }
}

/// One untranslated key with a propose action.
class _MissingKeyCard extends StatelessWidget {
  const _MissingKeyCard({
    required this.missingKey,
    required this.i18n,
    required this.onPropose,
    required this.busy,
  });

  final MissingKey missingKey;
  final I18nController i18n;
  final VoidCallback onPropose;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.translate, color: AppColors.primary),
        title: Text(missingKey.fullKey, style: AppTypography.titleMedium),
        subtitle: Text(
          missingKey.englishValue,
          style: AppTypography.bodyMedium,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: busy
            ? const SizedBox.square(
                dimension: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : TextButton(
                onPressed: onPropose,
                child: Text(i18n.t(StringKeys.suggestionsPropose)),
              ),
      ),
    );
  }
}

/// One of the caller's submissions with its review status.
class _SubmissionCard extends StatelessWidget {
  const _SubmissionCard({required this.suggestion, required this.i18n});

  final TranslationSuggestion suggestion;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final (label, state) = switch (suggestion.status) {
      'approved' => (
        i18n.t(StringKeys.suggestionsStatusApproved),
        PillState.success,
      ),
      'rejected' => (
        i18n.t(StringKeys.suggestionsStatusRejected),
        PillState.failure,
      ),
      _ => (i18n.t(StringKeys.suggestionsStatusPending), PillState.pending),
    };
    return Card(
      child: ListTile(
        leading: const Icon(Icons.translate, color: AppColors.primary),
        title: Text(suggestion.fullKey, style: AppTypography.titleMedium),
        subtitle: Text(
          suggestion.value,
          style: AppTypography.bodyMedium,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: StatusPill(label: label, state: state),
      ),
    );
  }
}
