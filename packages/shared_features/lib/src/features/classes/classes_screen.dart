/// Classes screen — educator tools (Phase 17/20).
///
/// Lists the caller's classes with their membership role, creates and
/// joins classes by invite code, and opens a class detail with the
/// member roster, assignments, and (for teachers) per-assignment
/// completion progress. All strings resolve through the typed
/// [StringKeys] registry.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_models/shared_models.dart';
import 'package:shared_ui/shared_ui.dart';
import 'package:shared_utils/shared_utils.dart';

import '../../app/app_scope.dart';
import '../../i18n/i18n_controller.dart';
import '../lessons/lessons_controller.dart';
import 'classes_controller.dart';

/// The educator browsing UI.
class ClassesScreen extends StatefulWidget {
  const ClassesScreen({super.key});

  @override
  State<ClassesScreen> createState() => _ClassesScreenState();
}

class _ClassesScreenState extends State<ClassesScreen> {
  @override
  void initState() {
    super.initState();
    // Prefetch the class list once per app instance (the shells build
    // every page eagerly via IndexedStack, so the first notifyListeners
    // must not run during build).
    final controller = context.read<ClassesController>();
    if (!controller.hasLoaded) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) controller.load();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final i18n = AppScope.of(context).i18n;
    final controller = context.watch<ClassesController>();

    return Scaffold(
      appBar: AppBar(title: Text(i18n.t(StringKeys.classesTitle))),
      floatingActionButton: controller.selected == null
          ? FloatingActionButton(
              tooltip: i18n.t(StringKeys.classesCreate),
              onPressed: () => _showCreateDialog(context),
              child: const Icon(Icons.group_add_outlined),
            )
          : null,
      body: _buildBody(context, i18n, controller),
    );
  }

  Widget _buildBody(
    BuildContext context,
    I18nController i18n,
    ClassesController controller,
  ) {
    // Detail view takes precedence when a class is open.
    if (controller.selected != null) {
      return _ClassDetail(controller: controller, i18n: i18n);
    }
    if (controller.state == ClassesFlowState.loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (controller.state == ClassesFlowState.failed) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            StatusPill(
              label: i18n.t(StringKeys.classesError),
              state: PillState.failure,
            ),
            const SizedBox(height: AppSpacing.md),
            AppButton(
              label: i18n.t(StringKeys.commonRetry),
              icon: Icons.refresh,
              onPressed: controller.load,
            ),
          ],
        ),
      );
    }
    if (controller.classes.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              StatusPill(label: i18n.t(StringKeys.classesEmpty)),
              const SizedBox(height: AppSpacing.md),
              AppButton(
                label: i18n.t(StringKeys.classesJoin),
                icon: Icons.login,
                onPressed: () => _showJoinDialog(context),
              ),
            ],
          ),
        ),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(AppSpacing.lg),
      itemCount: controller.classes.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: AppSpacing.sm),
      itemBuilder: (context, index) {
        if (index == controller.classes.length) {
          return OutlinedButton.icon(
            icon: const Icon(Icons.login),
            label: Text(i18n.t(StringKeys.classesJoin)),
            onPressed: () => _showJoinDialog(context),
          );
        }
        final room = controller.classes[index];
        return _ClassCard(
          room: room,
          i18n: i18n,
          onTap: () => _openClass(context, controller, room),
        );
      },
    );
  }
}

/// Open a class and surface fetch failures with a SnackBar.
Future<void> _openClass(
  BuildContext context,
  ClassesController controller,
  ClassRoom room,
) async {
  await controller.open(room.id);
  if (controller.selected == null &&
      controller.error != null &&
      context.mounted) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(controller.error!)));
  }
}

/// One class row: name, description, role, and invite code.
class _ClassCard extends StatelessWidget {
  const _ClassCard({
    required this.room,
    required this.i18n,
    required this.onTap,
  });

  final ClassRoom room;
  final I18nController i18n;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final roleLabel = room.isTeacher
        ? i18n.t(StringKeys.classesRoleTeacher)
        : i18n.t(StringKeys.classesRoleStudent);
    return Card(
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        leading: CircleAvatar(
          backgroundColor: AppColors.primaryContainer,
          child: Icon(
            room.isTeacher ? Icons.school_outlined : Icons.person_outline,
            color: AppColors.primary,
          ),
        ),
        title: Text(room.name, style: AppTypography.titleMedium),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (room.description.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.xxs),
              Text(
                room.description,
                style: AppTypography.bodyMedium,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            const SizedBox(height: AppSpacing.xs),
            Wrap(
              spacing: AppSpacing.xs,
              runSpacing: AppSpacing.xxs,
              children: [
                StatusPill(
                  label: roleLabel,
                  state: room.isTeacher ? PillState.neutral : PillState.pending,
                ),
                if (room.isTeacher && room.inviteCode.isNotEmpty)
                  StatusPill(
                    label:
                        '${i18n.t(StringKeys.classesInviteCode)} ${room.inviteCode}',
                    state: PillState.success,
                  ),
              ],
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}

/// The open class: roster, assignments, and teacher actions.
class _ClassDetail extends StatelessWidget {
  const _ClassDetail({required this.controller, required this.i18n});

  final ClassesController controller;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final room = controller.selected!;
    final members = room.members;
    final teachers = members.where((m) => m.isTeacher).toList();
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
              child: Text(room.name, style: AppTypography.headlineMedium),
            ),
          ],
        ),
        if (room.description.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(room.description, style: AppTypography.bodyLarge),
        ],
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            StatusPill(
              label: room.isTeacher
                  ? i18n.t(StringKeys.classesRoleTeacher)
                  : i18n.t(StringKeys.classesRoleStudent),
              state: room.isTeacher ? PillState.neutral : PillState.pending,
            ),
            if (room.isTeacher && room.inviteCode.isNotEmpty) ...[
              const SizedBox(width: AppSpacing.xs),
              StatusPill(
                label:
                    '${i18n.t(StringKeys.classesInviteCode)} ${room.inviteCode}',
                state: PillState.success,
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.lg),

        // Members (teacher-only roster actions).
        _SectionTitle(label: i18n.t(StringKeys.classesMembers)),
        const SizedBox(height: AppSpacing.xs),
        if (members.isEmpty)
          StatusPill(label: i18n.t(StringKeys.classesNoMembers))
        else
          Card(
            child: Column(
              children: [
                for (final member in members)
                  _MemberRow(
                    member: member,
                    i18n: i18n,
                    onRemove: room.isTeacher && !member.isTeacher
                        ? () => _confirmRemoveMember(context, member)
                        : null,
                  ),
              ],
            ),
          ),
        if (room.isTeacher && teachers.length > 1) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            '${teachers.length} ${i18n.t(StringKeys.classesRoleTeacher)}',
            style: AppTypography.labelMedium,
          ),
        ],
        const SizedBox(height: AppSpacing.lg),

        // Assignments.
        _SectionTitle(label: i18n.t(StringKeys.classesAssignments)),
        const SizedBox(height: AppSpacing.xs),
        if (room.assignments.isEmpty)
          StatusPill(label: i18n.t(StringKeys.classesNoAssignments))
        else
          for (final assignment in room.assignments) ...[
            _AssignmentCard(
              assignment: assignment,
              i18n: i18n,
              onRemove: room.isTeacher
                  ? () => _confirmUnassign(context, assignment)
                  : null,
            ),
            const SizedBox(height: AppSpacing.xs),
          ],
        if (room.isTeacher) ...[
          const SizedBox(height: AppSpacing.sm),
          AppButton(
            label: i18n.t(StringKeys.classesAssignLesson),
            icon: Icons.playlist_add,
            expanded: true,
            busy: controller.busy,
            onPressed: () => _showAssignDialog(context, room),
          ),
          const SizedBox(height: AppSpacing.sm),
          OutlinedButton.icon(
            icon: const Icon(Icons.insights_outlined),
            label: Text(i18n.t(StringKeys.classesProgress)),
            onPressed: () => _showProgressSheet(context, room),
          ),
          const SizedBox(height: AppSpacing.sm),
          OutlinedButton.icon(
            icon: const Icon(Icons.delete_outline),
            label: Text(i18n.t(StringKeys.classesDeleteClass)),
            style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
            onPressed: () => _confirmDeleteClass(context, room),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
      ],
    );
  }

  Future<void> _confirmRemoveMember(
    BuildContext context,
    ClassMember member,
  ) async {
    final confirmed = await _confirm(
      context,
      title: i18n.t(StringKeys.classesRemoveMember),
      message: member.displayName ?? member.userId,
    );
    if (confirmed == true && context.mounted) {
      final ok = await controller.removeMember(member.userId);
      if (!ok && context.mounted) _showError(context, controller);
    }
  }

  Future<void> _confirmUnassign(
    BuildContext context,
    Assignment assignment,
  ) async {
    final confirmed = await _confirm(
      context,
      title: i18n.t(StringKeys.classesRemoveAssignment),
      message: assignment.lessonTitle,
    );
    if (confirmed == true && context.mounted) {
      final ok = await controller.deleteAssignment(assignment.id);
      if (!ok && context.mounted) _showError(context, controller);
    }
  }

  Future<void> _confirmDeleteClass(BuildContext context, ClassRoom room) async {
    final confirmed = await _confirm(
      context,
      title: i18n.t(StringKeys.classesDeleteClass),
      message: room.name,
      destructive: true,
    );
    if (confirmed == true && context.mounted) {
      final ok = await controller.deleteClass();
      if (!ok && context.mounted) _showError(context, controller);
    }
  }

  Future<void> _showProgressSheet(BuildContext context, ClassRoom room) async {
    final busy = controller.busy;
    if (!busy) await controller.loadProgress();
    if (!context.mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) =>
          _ProgressSheet(controller: controller, i18n: i18n),
    );
  }
}

/// One roster row with an optional teacher-only remove action.
class _MemberRow extends StatelessWidget {
  const _MemberRow({required this.member, required this.i18n, this.onRemove});

  final ClassMember member;
  final I18nController i18n;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    final roleLabel = member.isTeacher
        ? i18n.t(StringKeys.classesRoleTeacher)
        : i18n.t(StringKeys.classesRoleStudent);
    return ListTile(
      dense: true,
      leading: Icon(
        member.isTeacher ? Icons.school_outlined : Icons.person_outline,
        color: member.isTeacher
            ? AppColors.primary
            : Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      title: Text(member.displayName ?? member.userId),
      subtitle: Text(roleLabel, style: AppTypography.labelMedium),
      trailing: onRemove == null
          ? null
          : IconButton(
              tooltip: i18n.t(StringKeys.classesRemoveMember),
              icon: const Icon(Icons.person_remove_outlined),
              onPressed: onRemove,
            ),
    );
  }
}

/// One assignment row with completion stats.
class _AssignmentCard extends StatelessWidget {
  const _AssignmentCard({
    required this.assignment,
    required this.i18n,
    this.onRemove,
  });

  final Assignment assignment;
  final I18nController i18n;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    final title = assignment.lessonTitle.isNotEmpty
        ? assignment.lessonTitle
        : assignment.lessonSlug;
    return Card(
      child: ListTile(
        leading: const Icon(Icons.menu_book_outlined, color: AppColors.primary),
        title: Text(title),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: AppSpacing.xxs),
            Text(
              i18n
                  .t(StringKeys.classesCompletedCount)
                  .replaceFirst('{completed}', '${assignment.completedCount}')
                  .replaceFirst('{total}', '${assignment.memberCount}'),
              style: AppTypography.labelMedium,
            ),
            if (assignment.dueAt != null) ...[
              const SizedBox(height: AppSpacing.xxs),
              Text(
                i18n
                    .t(StringKeys.classesDue)
                    .replaceFirst('{date}', _formatDate(assignment.dueAt!)),
                style: AppTypography.labelMedium,
              ),
            ],
          ],
        ),
        trailing: onRemove == null
            ? null
            : IconButton(
                tooltip: i18n.t(StringKeys.classesRemoveAssignment),
                icon: const Icon(Icons.remove_circle_outline),
                onPressed: onRemove,
              ),
      ),
    );
  }
}

/// Per-assignment, per-student completion (teacher view).
class _ProgressSheet extends StatelessWidget {
  const _ProgressSheet({required this.controller, required this.i18n});

  final ClassesController controller;
  final I18nController i18n;

  @override
  Widget build(BuildContext context) {
    final progress = controller.progress;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.lg,
          AppSpacing.xs,
          AppSpacing.lg,
          AppSpacing.lg,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              i18n.t(StringKeys.classesProgress),
              style: AppTypography.titleLarge,
            ),
            const SizedBox(height: AppSpacing.md),
            if (progress.isEmpty)
              StatusPill(label: i18n.t(StringKeys.classesNoAssignments))
            else
              Flexible(
                child: ListView.separated(
                  shrinkWrap: true,
                  itemCount: progress.length,
                  separatorBuilder: (_, _) =>
                      const SizedBox(height: AppSpacing.sm),
                  itemBuilder: (context, index) {
                    final item = progress[index];
                    final title = item.assignment.lessonTitle.isNotEmpty
                        ? item.assignment.lessonTitle
                        : item.assignment.lessonSlug;
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(title, style: AppTypography.titleMedium),
                            const SizedBox(height: AppSpacing.sm),
                            if (item.students.isEmpty)
                              Text(
                                i18n.t(StringKeys.classesNoMembers),
                                style: AppTypography.bodyMedium,
                              )
                            else
                              for (final student in item.students)
                                Row(
                                  children: [
                                    Icon(
                                      student.completed
                                          ? Icons.check_circle
                                          : Icons.radio_button_unchecked,
                                      size: 18,
                                      color: student.completed
                                          ? AppColors.success
                                          : Theme.of(
                                              context,
                                            ).colorScheme.onSurfaceVariant,
                                    ),
                                    const SizedBox(width: AppSpacing.xs),
                                    Expanded(
                                      child: Text(
                                        student.displayName ?? student.userId,
                                        style: AppTypography.bodyMedium,
                                      ),
                                    ),
                                    Text(
                                      i18n
                                          .t(StringKeys.classesCompletedCount)
                                          .replaceFirst(
                                            '{completed}',
                                            '${student.completed ? 1 : 0}',
                                          )
                                          .replaceFirst('{total}', '1'),
                                      style: AppTypography.labelMedium,
                                    ),
                                  ],
                                ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// A section heading inside the detail view.
class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(label, style: AppTypography.titleMedium);
  }
}

// --- dialogs ------------------------------------------------------------

void _showCreateDialog(BuildContext context) {
  final i18n = AppScope.of(context).i18n;
  final controller = context.read<ClassesController>();
  final nameController = TextEditingController();
  final descriptionController = TextEditingController();
  showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(i18n.t(StringKeys.classesCreate)),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: nameController,
            autofocus: true,
            decoration: InputDecoration(
              labelText: i18n.t(StringKeys.classesName),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          TextField(
            controller: descriptionController,
            decoration: InputDecoration(
              labelText: i18n.t(StringKeys.classesDescription),
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
            final name = nameController.text.trim();
            if (name.isEmpty) return;
            final ok = await controller.create(
              name,
              descriptionController.text.trim(),
            );
            if (dialogContext.mounted) {
              Navigator.of(dialogContext).pop();
              if (ok) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(i18n.t(StringKeys.classesCreateSuccess)),
                  ),
                );
              } else if (controller.error != null) {
                _showError(context, controller);
              }
            }
          },
          child: Text(i18n.t(StringKeys.classesCreate)),
        ),
      ],
    ),
  );
}

void _showJoinDialog(BuildContext context) {
  final i18n = AppScope.of(context).i18n;
  final controller = context.read<ClassesController>();
  final classIdController = TextEditingController();
  final codeController = TextEditingController();
  showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(i18n.t(StringKeys.classesJoin)),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            i18n.t(StringKeys.classesJoinHint),
            style: AppTypography.bodyMedium,
          ),
          const SizedBox(height: AppSpacing.md),
          TextField(
            controller: classIdController,
            autofocus: true,
            decoration: InputDecoration(
              labelText: i18n.t(StringKeys.classesClassId),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          TextField(
            controller: codeController,
            decoration: InputDecoration(
              labelText: i18n.t(StringKeys.classesInviteCode),
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
            final classId = classIdController.text.trim();
            final code = codeController.text.trim().toUpperCase();
            if (classId.isEmpty || code.isEmpty) return;
            final ok = await controller.join(classId, code);
            if (dialogContext.mounted) {
              Navigator.of(dialogContext).pop();
              if (!ok && controller.error != null) {
                _showError(context, controller);
              }
            }
          },
          child: Text(i18n.t(StringKeys.classesJoin)),
        ),
      ],
    ),
  );
}

void _showAssignDialog(BuildContext context, ClassRoom room) {
  final i18n = AppScope.of(context).i18n;
  final lessons = context.read<LessonsController>();
  final classes = context.read<ClassesController>();
  showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(i18n.t(StringKeys.classesAssignLesson)),
      content: SizedBox(
        width: double.maxFinite,
        child: _LessonPicker(
          lessons: lessons,
          classes: classes,
          i18n: i18n,
          room: room,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(),
          child: Text(i18n.t(StringKeys.commonCancel)),
        ),
      ],
    ),
  );
}

/// The list of assignable lessons (from the shared curriculum controller).
class _LessonPicker extends StatefulWidget {
  const _LessonPicker({
    required this.lessons,
    required this.classes,
    required this.i18n,
    required this.room,
  });

  final LessonsController lessons;
  final ClassesController classes;
  final I18nController i18n;
  final ClassRoom room;

  @override
  State<_LessonPicker> createState() => _LessonPickerState();
}

class _LessonPickerState extends State<_LessonPicker> {
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    if (!widget.lessons.hasLoaded && widget.lessons.lessons.isEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        widget.lessons.load(widget.i18n.locale);
      });
    }
    widget.lessons.addListener(_onLessonsChanged);
  }

  @override
  void dispose() {
    widget.lessons.removeListener(_onLessonsChanged);
    super.dispose();
  }

  void _onLessonsChanged() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final lessons = widget.lessons;
    if (!lessons.hasLoaded) {
      return const Padding(
        padding: EdgeInsets.all(AppSpacing.md),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (lessons.lessons.isEmpty) {
      return StatusPill(label: widget.i18n.t(StringKeys.lessonsEmpty));
    }
    final assignedIds = widget.room.assignments
        .map((assignment) => assignment.lessonId)
        .toSet();
    return ListView(
      shrinkWrap: true,
      children: [
        for (final lesson in lessons.lessons) ...[
          ListTile(
            enabled: !assignedIds.contains(lesson.id),
            leading: Icon(
              assignedIds.contains(lesson.id)
                  ? Icons.check
                  : Icons.menu_book_outlined,
              color: assignedIds.contains(lesson.id)
                  ? AppColors.success
                  : AppColors.primary,
            ),
            title: Text(lesson.title ?? lesson.slug),
            onTap: _busy
                ? null
                : () async {
                    setState(() => _busy = true);
                    final controller = widget.classes;
                    final messenger = ScaffoldMessenger.of(context);
                    final navigator = Navigator.of(context);
                    final ok = await controller.assignLesson(lesson.slug);
                    if (!mounted) return;
                    setState(() => _busy = false);
                    if (ok) {
                      navigator.pop();
                    } else if (controller.error != null) {
                      messenger.showSnackBar(
                        SnackBar(content: Text(controller.error!)),
                      );
                    }
                  },
          ),
          const Divider(height: 1),
        ],
      ],
    );
  }
}

// --- helpers ------------------------------------------------------------

Future<bool?> _confirm(
  BuildContext context, {
  required String title,
  required String message,
  bool destructive = false,
}) {
  final i18n = AppScope.of(context).i18n;
  return showDialog<bool>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(false),
          child: Text(i18n.t(StringKeys.commonCancel)),
        ),
        FilledButton(
          style: destructive
              ? FilledButton.styleFrom(backgroundColor: AppColors.danger)
              : null,
          onPressed: () => Navigator.of(dialogContext).pop(true),
          child: Text(title),
        ),
      ],
    ),
  );
}

void _showError(BuildContext context, ClassesController controller) {
  ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(controller.error ?? 'Error')));
}

String _formatDate(DateTime date) {
  final local = date.toLocal();
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  return '$day/$month/${local.year}';
}
