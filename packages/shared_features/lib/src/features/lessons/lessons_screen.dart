/// Lessons screen — the media-literacy curriculum (Phase 15/16).
///
/// Lists the localized lessons with per-user progress, opens a lesson
/// detail with its content sections, and marks lessons complete. All
/// strings resolve through the typed [StringKeys] registry.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import 'lessons_controller.dart';

/// The curriculum browsing UI.
class LessonsScreen extends StatefulWidget {
  const LessonsScreen({super.key});

  @override
  State<LessonsScreen> createState() => _LessonsScreenState();
}

class _LessonsScreenState extends State<LessonsScreen> {
  I18nController? _i18n;

  @override
  void initState() {
    super.initState();
    // Prefetch the curriculum once per app instance (shells build all
    // pages eagerly via IndexedStack, so the first notifyListeners must
    // not run during build). Reloads are user-driven (retry) or follow a
    // locale change in settings.
    final controller = context.read<LessonsController>();
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
    final controller = context.read<LessonsController>();
    if (controller.selected == null && controller.hasLoaded) {
      controller.load(_i18n!.locale);
    }
  }

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.watch<LessonsController>();

    return Scaffold(body: _buildBody(context, i18n, controller));
  }

  Widget _buildBody(
    BuildContext context,
    I18nController i18n,
    LessonsController controller,
  ) {
    // Detail view takes precedence when a lesson is open.
    if (controller.selected != null) {
      return _LessonDetail(controller: controller, i18n: i18n);
    }

    final header = Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: PageHeader(
        icon: Icons.menu_book_outlined,
        title: i18n.t(StringKeys.lessonsTitle),
        subtitle: i18n.t(StringKeys.lessonsSubtitle),
      ),
    );

    if (controller.state == LessonsFlowState.loading) {
      return Column(
        children: [
          header,
          const Expanded(child: Center(child: CircularProgressIndicator())),
        ],
      );
    }
    if (controller.state == LessonsFlowState.failed) {
      return Column(
        children: [
          header,
          Expanded(
            child: AppErrorState(
              title: i18n.t(StringKeys.lessonsError),
              action: StateAction(
                label: i18n.t(StringKeys.commonRetry),
                icon: Icons.refresh,
                onPressed: () => controller.load(i18n.locale),
              ),
            ),
          ),
        ],
      );
    }
    if (controller.lessons.isEmpty) {
      return Column(
        children: [
          header,
          Expanded(
            child: AppEmptyState(
              title: i18n.t(StringKeys.lessonsEmpty),
              icon: Icons.menu_book_outlined,
            ),
          ),
        ],
      );
    }
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        header,
        const SizedBox(height: AppSpacing.xs),
        for (final lesson in controller.lessons) ...[
          _LessonCard(
            lesson: lesson,
            i18n: i18n,
            onTap: () => _openLesson(context, controller, lesson),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
      ],
    );
  }
}

/// Open a lesson and surface fetch failures (e.g. a missing lesson) with
/// a transient SnackBar instead of failing silently.
Future<void> _openLesson(
  BuildContext context,
  LessonsController controller,
  Lesson lesson,
) async {
  final i18n = AppScope.of(context).i18n;
  await controller.open(lesson.id, locale: i18n.locale);
  if (controller.selected == null &&
      controller.error != null &&
      context.mounted) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(controller.error!)));
  }
}

/// The localized name of a lesson difficulty level.
String difficultyLabel(String difficulty, I18nController i18n) {
  switch (difficulty) {
    case 'beginner':
      return i18n.t(StringKeys.lessonsDifficultyBeginner);
    case 'intermediate':
      return i18n.t(StringKeys.lessonsDifficultyIntermediate);
    case 'advanced':
      return i18n.t(StringKeys.lessonsDifficultyAdvanced);
    default:
      return difficulty;
  }
}

/// One curriculum row: title, summary, difficulty, and progress.
class _LessonCard extends StatelessWidget {
  const _LessonCard({
    required this.lesson,
    required this.i18n,
    required this.onTap,
  });

  final Lesson lesson;
  final I18nController i18n;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final completed = lesson.completed;
    return Card(
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        leading: Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: completed
                ? AppColors.success.withValues(alpha: 0.12)
                : colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
          ),
          child: Icon(
            completed ? Icons.check_rounded : Icons.menu_book_outlined,
            color: completed ? AppColors.success : colorScheme.primary,
            size: 24,
          ),
        ),
        title: Text(
          lesson.title ?? lesson.slug,
          style: AppTypography.titleMedium,
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (lesson.summary != null && lesson.summary!.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xxs),
              Text(
                lesson.summary!,
                style: AppTypography.bodyMedium,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: AppSpacing.xs),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xxs,
              children: [
                StatusPill(
                  label: difficultyLabel(lesson.difficulty, i18n),
                  state: PillState.neutral,
                ),
                StatusPill(
                  label: i18n
                      .t(StringKeys.lessonsMinutes)
                      .replaceFirst('{minutes}', '${lesson.estimatedMinutes}'),
                  state: PillState.neutral,
                ),
                if (completed)
                  StatusPill(
                    label: i18n.t(StringKeys.lessonsCompleted),
                    state: PillState.success,
                  ),
              ],
            ),
          ],
        ),
        trailing: Icon(
          Icons.chevron_right,
          color: colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

/// The open lesson: summary, sections, and a completion action.
class _LessonDetail extends StatelessWidget {
  const _LessonDetail({required this.controller, required this.i18n});

  final LessonsController controller;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final lesson = controller.selected!;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      children: [
        Row(
          children: [
            IconButton(
              tooltip: i18n.t(StringKeys.commonClose),
              icon: const Icon(Icons.arrow_back),
              onPressed: controller.closeDetail,
            ),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: Text(
                lesson.title ?? lesson.slug,
                style: AppTypography.headlineLarge,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        Wrap(
          spacing: AppSpacing.xs,
          runSpacing: AppSpacing.xxs,
          children: [
            StatusPill(
              label: difficultyLabel(lesson.difficulty, i18n),
              state: PillState.neutral,
            ),
            StatusPill(
              label: i18n
                  .t(StringKeys.lessonsMinutes)
                  .replaceFirst('{minutes}', '${lesson.estimatedMinutes}'),
              state: PillState.neutral,
            ),
            if (lesson.completed)
              StatusPill(
                label: i18n.t(StringKeys.lessonsCompleted),
                state: PillState.success,
              ),
          ],
        ),
        if (lesson.summary != null && lesson.summary!.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Text(lesson.summary!, style: AppTypography.bodyLarge),
        ],
        const SizedBox(height: AppSpacing.lg),
        for (final section in lesson.sections) ...[
          _SectionBlock(section: section),
          const SizedBox(height: AppSpacing.lg),
        ],
        const SizedBox(height: AppSpacing.sm),
        AppButton(
          label: lesson.completed
              ? i18n.t(StringKeys.lessonsCompleted)
              : i18n.t(StringKeys.lessonsComplete),
          icon: lesson.completed ? Icons.check : Icons.done_all,
          busy: controller.busy,
          expanded: true,
          onPressed: lesson.completed
              ? null
              : () => controller.complete(locale: i18n.locale),
        ),
      ],
    );
  }
}

/// One content section: heading, body, and optional bullets.
class _SectionBlock extends StatelessWidget {
  const _SectionBlock({required this.section});

  final LessonSection section;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(section.heading, style: AppTypography.titleLarge),
            const SizedBox(height: AppSpacing.xs),
            Text(section.body, style: AppTypography.bodyLarge),
            if (section.bullets.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              for (final bullet in section.bullets)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.xxs),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('•  '),
                      Expanded(
                        child: Text(bullet, style: AppTypography.bodyMedium),
                      ),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
