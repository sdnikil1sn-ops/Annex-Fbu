/// Stable, typed string keys (ADR-0007).
///
/// UI code references these constants instead of hardcoded prose; the
/// backend resolves them into localized text via versioned bundles
/// (`GET /v1/i18n/bundles/{locale}`). A key lives here first (base
/// locale English), then in the server-side translation data.
library;

/// The canonical registry of every user-facing string key.
///
/// Keys follow the `namespace.key` convention and mirror the backend
/// `i18n_translations` seed data. Adding a key here is the first step of
/// introducing any user-facing string; hardcoding prose is rejected by
/// the project's i18n lint rule.
abstract final class StringKeys {
  // common
  static const commonCancel = 'common.cancel';
  static const commonSave = 'common.save';
  static const commonRetry = 'common.retry';
  static const commonLoading = 'common.loading';
  static const commonClose = 'common.close';
  static const commonLearnBeforeYouBelieve = 'common.learn_before_you_believe';
  static const commonClaimsCount = 'common.claims_count';

  // analysis
  static const analysisSubmit = 'analysis.submit';
  static const analysisPending = 'analysis.pending';
  static const analysisProcessing = 'analysis.processing';
  static const analysisCompleted = 'analysis.completed';
  static const analysisFailed = 'analysis.failed';
  static const analysisSummary = 'analysis.summary';
  static const analysisCredibilityScore = 'analysis.credibility_score';
  static const analysisVerifiability = 'analysis.verifiability';
  static const analysisTitle = 'analysis.title';
  static const analysisInputHint = 'analysis.input_hint';

  // auth
  static const authSignIn = 'auth.sign_in';
  static const authSignOut = 'auth.sign_out';
  static const authContinueGuest = 'auth.continue_guest';
  static const authContinueGoogle = 'auth.continue_google';
  static const authGuestLabel = 'auth.guest_label';

  // lessons (Phase 15/16)
  static const lessonsTitle = 'lessons.title';
  static const lessonsComplete = 'lessons.complete';
  static const lessonsCompleted = 'lessons.completed';
  static const lessonsMinutes = 'lessons.minutes';
  static const lessonsDifficulty = 'lessons.difficulty';
  static const lessonsDifficultyBeginner = 'lessons.difficulty_beginner';
  static const lessonsDifficultyIntermediate =
      'lessons.difficulty_intermediate';
  static const lessonsDifficultyAdvanced = 'lessons.difficulty_advanced';
  static const lessonsEmpty = 'lessons.empty';
  static const lessonsError = 'lessons.error';

  // classes (Phase 17/20)
  static const classesTitle = 'classes.title';
  static const classesCreate = 'classes.create';
  static const classesJoin = 'classes.join';
  static const classesInviteCode = 'classes.invite_code';
  static const classesName = 'classes.name';
  static const classesDescription = 'classes.description';
  static const classesMembers = 'classes.members';
  static const classesAssignments = 'classes.assignments';
  static const classesAssignLesson = 'classes.assign_lesson';
  static const classesProgress = 'classes.progress';
  static const classesRoleTeacher = 'classes.role_teacher';
  static const classesRoleStudent = 'classes.role_student';
  static const classesEmpty = 'classes.empty';
  static const classesError = 'classes.error';
  static const classesCompletedCount = 'classes.completed_count';
  static const classesDeleteClass = 'classes.delete_class';
  static const classesRemoveMember = 'classes.remove_member';
  static const classesRemoveAssignment = 'classes.remove_assignment';
  static const classesStudents = 'classes.students';
  static const classesNoAssignments = 'classes.no_assignments';
  static const classesNoMembers = 'classes.no_members';
  static const classesDue = 'classes.due';
  static const classesClassId = 'classes.class_id';
  static const classesJoinHint = 'classes.join_hint';
  static const classesCreateSuccess = 'classes.create_success';

  // settings
  static const settingsTitle = 'settings.title';
  static const settingsLanguage = 'settings.language';
  static const settingsTheme = 'settings.theme';
  static const settingsThemeSystem = 'settings.theme_system';
  static const settingsThemeLight = 'settings.theme_light';
  static const settingsThemeDark = 'settings.theme_dark';
  static const settingsAccount = 'settings.account';

  // errors
  static const errorsGeneric = 'errors.generic';
  static const errorsNotFound = 'errors.not_found';
  static const errorsRateLimited = 'errors.rate_limited';

  /// Every registered key, for validation and codegen.
  static const List<String> all = [
    commonCancel,
    commonSave,
    commonRetry,
    commonLoading,
    commonClose,
    commonLearnBeforeYouBelieve,
    commonClaimsCount,
    analysisSubmit,
    analysisPending,
    analysisProcessing,
    analysisCompleted,
    analysisFailed,
    analysisSummary,
    analysisCredibilityScore,
    analysisVerifiability,
    analysisTitle,
    analysisInputHint,
    authSignIn,
    authSignOut,
    authContinueGuest,
    authContinueGoogle,
    authGuestLabel,
    lessonsTitle,
    lessonsComplete,
    lessonsCompleted,
    lessonsMinutes,
    lessonsDifficulty,
    lessonsDifficultyBeginner,
    lessonsDifficultyIntermediate,
    lessonsDifficultyAdvanced,
    lessonsEmpty,
    lessonsError,
    classesTitle,
    classesCreate,
    classesJoin,
    classesInviteCode,
    classesName,
    classesDescription,
    classesMembers,
    classesAssignments,
    classesAssignLesson,
    classesProgress,
    classesRoleTeacher,
    classesRoleStudent,
    classesEmpty,
    classesError,
    classesCompletedCount,
    classesDeleteClass,
    classesRemoveMember,
    classesRemoveAssignment,
    classesStudents,
    classesNoAssignments,
    classesNoMembers,
    classesDue,
    classesClassId,
    classesJoinHint,
    classesCreateSuccess,
    settingsTitle,
    settingsLanguage,
    settingsTheme,
    settingsThemeSystem,
    settingsThemeLight,
    settingsThemeDark,
    settingsAccount,
    errorsGeneric,
    errorsNotFound,
    errorsRateLimited,
  ];

  static final RegExp _keyPattern =
      RegExp(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$');

  /// Whether [key] is a well-formed `namespace.key` string.
  static bool isValid(String key) => _keyPattern.hasMatch(key);

  /// Whether [key] is a registered key from this registry.
  static bool isKnown(String key) => all.contains(key);

  /// The namespace portion of a well-formed key (`ns.key` -> `ns`).
  ///
  /// Returns null for keys that are not well-formed.
  static String? namespaceOf(String key) {
    if (!isValid(key)) return null;
    return key.split('.').first;
  }
}
