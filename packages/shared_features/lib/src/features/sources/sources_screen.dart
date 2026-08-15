/// Source registry screen — credibility (Phase 14/19/22).
///
/// Searches publishers/domains, opens a profile showing the model
/// credibility score and trust signals alongside the aggregated
/// community signal (count + average), and lets authenticated users rate
/// a source 1–5 — the registry grows more accurate the more it is used.
/// All strings resolve through the typed [StringKeys] registry.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import 'sources_controller.dart';

/// The source registry browsing UI.
class SourcesScreen extends StatefulWidget {
  const SourcesScreen({super.key});

  @override
  State<SourcesScreen> createState() => _SourcesScreenState();
}

class _SourcesScreenState extends State<SourcesScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.watch<SourcesController>();

    return Scaffold(
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.xs,
            ),
            child: PageHeader(
              icon: Icons.public_outlined,
              title: i18n.t(StringKeys.sourcesTitle),
              subtitle: i18n.t(StringKeys.sourcesSubtitle),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.xs,
              AppSpacing.lg,
              AppSpacing.md,
            ),
            child: TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              decoration: InputDecoration(
                hintText: i18n.t(StringKeys.sourcesSearchHint),
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  tooltip: i18n.t(StringKeys.sourcesSearch),
                  icon: controller.busy
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.arrow_forward_rounded),
                  onPressed: controller.busy
                      ? null
                      : () => controller.search(_searchController.text),
                ),
              ),
              onSubmitted: (value) => controller.search(value),
            ),
          ),
          Expanded(child: _buildBody(context, i18n, controller)),
        ],
      ),
    );
  }

  Widget _buildBody(
    BuildContext context,
    I18nController i18n,
    SourcesController controller,
  ) {
    // Profile view takes precedence when a source is open.
    if (controller.selected != null) {
      return _SourceProfile(controller: controller, i18n: i18n);
    }
    if (controller.state == SourcesFlowState.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (controller.state == SourcesFlowState.failed) {
      return AppErrorState(
        title: i18n.t(StringKeys.sourcesError),
        action: StateAction(
          label: i18n.t(StringKeys.commonRetry),
          icon: Icons.refresh,
          onPressed: () => controller.search(controller.query),
        ),
      );
    }
    if (controller.hasSearched && controller.results.isEmpty) {
      return AppEmptyState(
        title: i18n.t(StringKeys.sourcesNoResults),
        icon: Icons.search_off_rounded,
      );
    }
    if (!controller.hasSearched) {
      return AppEmptyState(
        title: i18n.t(StringKeys.sourcesSearchHint),
        icon: Icons.travel_explore_rounded,
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(AppSpacing.lg),
      itemCount: controller.results.length,
      separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.sm),
      itemBuilder: (context, index) {
        final source = controller.results[index];
        return _SourceCard(
          source: source,
          i18n: i18n,
          onTap: () => _openProfile(context, controller, source),
        );
      },
    );
  }
}

/// Open a source and surface fetch failures with a SnackBar.
Future<void> _openProfile(
  BuildContext context,
  SourcesController controller,
  Source source,
) async {
  await controller.open(source.domain);
  if (controller.selected == null &&
      controller.error != null &&
      context.mounted) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(controller.error!)));
  }
}

/// One search result: name/domain, model score, and community count.
class _SourceCard extends StatelessWidget {
  const _SourceCard({
    required this.source,
    required this.i18n,
    required this.onTap,
  });

  final Source source;
  final I18nController i18n;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final score = source.score;
    return Card(
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        leading: Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
          ),
          child: Icon(
            source.category == 'fact_check'
                ? Icons.verified_outlined
                : Icons.public,
            color: AppColors.primary,
            size: 24,
          ),
        ),
        title: Text(
          source.name ?? source.domain,
          style: AppTypography.titleMedium,
        ),
        subtitle: Text(source.domain, style: AppTypography.labelMedium),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (score != null)
              Text(
                '${(score * 100).round()}%',
                style: AppTypography.titleMedium.copyWith(
                  color: scoreColor(scoreBandFor(score)),
                ),
              ),
            if (source.community.count > 0) ...[
              const SizedBox(height: AppSpacing.xxs),
              Text(
                i18n
                    .t(StringKeys.sourcesRatingsCount)
                    .replaceFirst('{count}', '${source.community.count}'),
                style: AppTypography.labelMedium,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// The open source profile: scores, signals, and community rating.
class _SourceProfile extends StatelessWidget {
  const _SourceProfile({required this.controller, required this.i18n});

  final SourcesController controller;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final source = controller.selected!;
    final score = source.score;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        Row(
          children: [
            IconButton(
              tooltip: i18n.t(StringKeys.commonClose),
              icon: const Icon(Icons.arrow_back),
              onPressed: controller.closeProfile,
            ),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: Text(
                source.name ?? source.domain,
                style: AppTypography.headlineMedium,
              ),
            ),
          ],
        ),
        Text(source.domain, style: AppTypography.labelMedium),
        if (source.category != null) ...[
          const SizedBox(height: AppSpacing.xs),
          StatusPill(label: source.category!, state: PillState.neutral),
        ],
        const SizedBox(height: AppSpacing.lg),

        // Model score vs community signal side by side.
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            if (score != null)
              ScoreMeter(
                score: score,
                label: i18n.t(StringKeys.sourcesModelScore),
              ),
            _CommunityColumn(source: source, i18n: i18n),
          ],
        ),
        const SizedBox(height: AppSpacing.lg),

        // Community rating control (one voice per user).
        if (source.community.hasRated) ...[
          Text(
            i18n.t(StringKeys.sourcesYourRating),
            style: AppTypography.titleMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          _RatingStars(rating: source.community.myRating ?? 0, onChanged: null),
          const SizedBox(height: AppSpacing.lg),
        ] else ...[
          Text(
            i18n.t(StringKeys.sourcesRate),
            style: AppTypography.titleMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          _RatingStars(
            rating: 0,
            onChanged: (rating) => _rate(context, controller, rating),
            busy: controller.busy,
          ),
          const SizedBox(height: AppSpacing.lg),
        ],

        // Trust signals backing the model score.
        if (source.signals.isNotEmpty) ...[
          Text(
            i18n.t(StringKeys.sourcesTrustSignals),
            style: AppTypography.titleMedium,
          ),
          const SizedBox(height: AppSpacing.xs),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                children: [
                  for (final entry in source.signals.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.check_circle_outline,
                            size: 18,
                            color: AppColors.success,
                          ),
                          const SizedBox(width: AppSpacing.xs),
                          Expanded(
                            child: Text(
                              '${entry.key}: ${entry.value}',
                              style: AppTypography.bodyMedium,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
      ],
    );
  }

  Future<void> _rate(
    BuildContext context,
    SourcesController controller,
    int rating,
  ) async {
    final ok = await controller.rate(rating);
    if (!ok && controller.error != null && context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(controller.error!)));
    }
  }
}

/// The aggregated community signal: count + average.
class _CommunityColumn extends StatelessWidget {
  const _CommunityColumn({required this.source, required this.i18n});

  final Source source;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final community = source.community;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '★ ${community.average?.toStringAsFixed(1) ?? '–'}',
          style: AppTypography.headlineMedium.copyWith(
            color: AppColors.warning,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          i18n.t(StringKeys.sourcesCommunity),
          style: AppTypography.labelMedium.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: AppSpacing.xxs),
        Text(
          community.count == 0
              ? i18n.t(StringKeys.sourcesCommunityEmpty)
              : i18n
                    .t(StringKeys.sourcesRatingsCount)
                    .replaceFirst('{count}', '${community.count}'),
          style: AppTypography.labelMedium,
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

/// A 1–5 star rating row (read-only or interactive).
class _RatingStars extends StatelessWidget {
  const _RatingStars({
    required this.rating,
    required this.onChanged,
    this.busy = false,
  });

  /// The current rating (0 = none).
  final int rating;

  /// Callback with the tapped rating; null renders read-only.
  final ValueChanged<int>? onChanged;

  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var star = 1; star <= 5; star++)
          IconButton(
            tooltip: '$star',
            onPressed: busy || onChanged == null
                ? null
                : () => onChanged!(star),
            icon: Icon(
              star <= rating ? Icons.star : Icons.star_border,
              color: star <= rating ? AppColors.warning : null,
            ),
          ),
      ],
    );
  }
}
