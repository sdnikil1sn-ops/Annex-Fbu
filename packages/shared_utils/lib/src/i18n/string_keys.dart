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
  static const commonAppTagline = 'common.app_tagline';
  static const commonOpenSourceNote = 'common.open_source_note';

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
  static const analysisSubtitle = 'analysis.subtitle';
  static const analysisInputHint = 'analysis.input_hint';

  // auth
  static const authSignIn = 'auth.sign_in';
  static const authSignInTab = 'auth.sign_in_tab';
  static const authSignUp = 'auth.sign_up';
  static const authSignOut = 'auth.sign_out';
  static const authEmail = 'auth.email';
  static const authPassword = 'auth.password';
  static const authConfirmPassword = 'auth.confirm_password';
  static const authOrContinue = 'auth.or_continue';
  static const authCreateAccount = 'auth.create_account';
  static const authHaveAccount = 'auth.have_account';
  static const authInvalidEmail = 'auth.invalid_email';
  static const authPasswordTooShort = 'auth.password_too_short';
  static const authPasswordTooWeak = 'auth.password_too_weak';
  static const authPasswordsDontMatch = 'auth.passwords_dont_match';
  static const authContinueGuest = 'auth.continue_guest';
  static const authContinueGoogle = 'auth.continue_google';
  static const authGuestLabel = 'auth.guest_label';
  static const authPrivacyNote = 'auth.privacy_note';
  static const authFeatureAnalyze = 'auth.feature_analyze';
  static const authFeatureSources = 'auth.feature_sources';
  static const authFeatureLessons = 'auth.feature_lessons';
  static const authErrorWrongPassword = 'auth.error_wrong_password';
  static const authErrorUserNotFound = 'auth.error_user_not_found';
  static const authErrorEmailInUse = 'auth.error_email_in_use';
  static const authErrorWeakPassword = 'auth.error_weak_password';
  static const authErrorInvalidCredential = 'auth.error_invalid_credential';
  static const authErrorTooManyRequests = 'auth.error_too_many_requests';
  static const authErrorNetwork = 'auth.error_network';
  static const authErrorDefault = 'auth.error_default';

  // analysis input modes (image analysis)
  static const analysisModeText = 'analysis.mode_text';
  static const analysisModeImage = 'analysis.mode_image';
  static const analysisImageHint = 'analysis.image_hint';
  static const analysisImageChoose = 'analysis.image_choose';
  static const analysisImageChange = 'analysis.image_change';
  static const analysisImageSubmit = 'analysis.image_submit';
  static const analysisImageOcr = 'analysis.image_ocr';
  static const analysisImageForensics = 'analysis.image_forensics';
  static const analysisImageRisk = 'analysis.image_risk';
  static const analysisImageSignals = 'analysis.image_signals';
  static const analysisImageDimensions = 'analysis.image_dimensions';

  // lessons (Phase 15/16)
  static const lessonsTitle = 'lessons.title';
  static const lessonsSubtitle = 'lessons.subtitle';
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
  static const classesSubtitle = 'classes.subtitle';
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

  // suggestions (Phase 18/21)
  static const suggestionsTitle = 'suggestions.title';
  static const suggestionsSubtitle = 'suggestions.subtitle';
  static const suggestionsMissing = 'suggestions.missing';
  static const suggestionsPropose = 'suggestions.propose';
  static const suggestionsYourSubmissions = 'suggestions.your_submissions';
  static const suggestionsEmpty = 'suggestions.empty';
  static const suggestionsError = 'suggestions.error';
  static const suggestionsNoSubmissions = 'suggestions.no_submissions';
  static const suggestionsValue = 'suggestions.value';
  static const suggestionsEnglish = 'suggestions.english';
  static const suggestionsStatusPending = 'suggestions.status_pending';
  static const suggestionsStatusApproved = 'suggestions.status_approved';
  static const suggestionsStatusRejected = 'suggestions.status_rejected';
  static const suggestionsSubmitted = 'suggestions.submitted';
  static const suggestionsLocale = 'suggestions.locale';
  static const suggestionsContributorNote = 'suggestions.contributor_note';
  static const suggestionsReviewQueue = 'suggestions.review_queue';
  static const suggestionsApprove = 'suggestions.approve';
  static const suggestionsReject = 'suggestions.reject';
  static const suggestionsNoPending = 'suggestions.no_pending';

  // sources (Phase 14/19/22)
  static const sourcesTitle = 'sources.title';
  static const sourcesSubtitle = 'sources.subtitle';
  static const sourcesSearchHint = 'sources.search_hint';
  static const sourcesSearch = 'sources.search';
  static const sourcesModelScore = 'sources.model_score';
  static const sourcesCommunity = 'sources.community';
  static const sourcesRate = 'sources.rate';
  static const sourcesYourRating = 'sources.your_rating';
  static const sourcesNoResults = 'sources.no_results';
  static const sourcesError = 'sources.error';
  static const sourcesTrustSignals = 'sources.trust_signals';
  static const sourcesRatingsCount = 'sources.ratings_count';
  static const sourcesAverage = 'sources.average';
  static const sourcesScoreLabel = 'sources.score_label';
  static const sourcesCommunityEmpty = 'sources.community_empty';
  static const sourcesOpenProfile = 'sources.open_profile';

  // settings
  static const settingsTitle = 'settings.title';
  static const settingsSubtitle = 'settings.subtitle';
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
    commonAppTagline,
    commonOpenSourceNote,
    analysisSubmit,
    analysisPending,
    analysisProcessing,
    analysisCompleted,
    analysisFailed,
    analysisSummary,
    analysisCredibilityScore,
    analysisVerifiability,
    analysisTitle,
    analysisSubtitle,
    analysisInputHint,
    authSignIn,
    authSignInTab,
    authSignUp,
    authSignOut,
    authEmail,
    authPassword,
    authConfirmPassword,
    authOrContinue,
    authCreateAccount,
    authHaveAccount,
    authInvalidEmail,
    authPasswordTooShort,
    authPasswordTooWeak,
    authPasswordsDontMatch,
    authContinueGuest,
    authContinueGoogle,
    authGuestLabel,
    authPrivacyNote,
    authFeatureAnalyze,
    authFeatureSources,
    authFeatureLessons,
    authErrorWrongPassword,
    authErrorUserNotFound,
    authErrorEmailInUse,
    authErrorWeakPassword,
    authErrorInvalidCredential,
    authErrorTooManyRequests,
    authErrorNetwork,
    authErrorDefault,
    analysisModeText,
    analysisModeImage,
    analysisImageHint,
    analysisImageChoose,
    analysisImageChange,
    analysisImageSubmit,
    analysisImageOcr,
    analysisImageForensics,
    analysisImageRisk,
    analysisImageSignals,
    analysisImageDimensions,
    lessonsTitle,
    lessonsSubtitle,
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
    classesSubtitle,
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
    suggestionsTitle,
    suggestionsSubtitle,
    suggestionsMissing,
    suggestionsPropose,
    suggestionsYourSubmissions,
    suggestionsEmpty,
    suggestionsError,
    suggestionsNoSubmissions,
    suggestionsValue,
    suggestionsEnglish,
    suggestionsStatusPending,
    suggestionsStatusApproved,
    suggestionsStatusRejected,
    suggestionsSubmitted,
    suggestionsLocale,
    suggestionsContributorNote,
    suggestionsReviewQueue,
    suggestionsApprove,
    suggestionsReject,
    suggestionsNoPending,
    sourcesTitle,
    sourcesSubtitle,
    sourcesSearchHint,
    sourcesSearch,
    sourcesModelScore,
    sourcesCommunity,
    sourcesRate,
    sourcesYourRating,
    sourcesNoResults,
    sourcesError,
    sourcesTrustSignals,
    sourcesRatingsCount,
    sourcesAverage,
    sourcesScoreLabel,
    sourcesCommunityEmpty,
    sourcesOpenProfile,
    settingsTitle,
    settingsSubtitle,
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

/// Base (English) values for every registered key.
///
/// Used by the clients only as a last-resort fallback so the UI never
/// renders a raw key while a translation bundle is loading or the backend
/// is unreachable. When the backend bundle resolves, its (possibly
/// server-updated) value always wins. New keys must be added here and to
/// [StringKeys.all] in the same commit.
const Map<String, String> defaultEnglishValues = {
  // common
  StringKeys.commonCancel: 'Cancel',
  StringKeys.commonSave: 'Save',
  StringKeys.commonRetry: 'Retry',
  StringKeys.commonLoading: 'Loading…',
  StringKeys.commonClose: 'Close',
  StringKeys.commonLearnBeforeYouBelieve: 'Learn before you believe.',
  StringKeys.commonClaimsCount: '{count} claims',
  StringKeys.commonAppTagline: 'AI-powered media & information literacy.',
  StringKeys.commonOpenSourceNote: 'Open source · Free forever · Multilingual',

  // analysis
  StringKeys.analysisSubmit: 'Analyze',
  StringKeys.analysisPending: 'Analysis in progress…',
  StringKeys.analysisProcessing: 'Analyzing…',
  StringKeys.analysisCompleted: 'Analysis complete',
  StringKeys.analysisFailed: 'Analysis failed',
  StringKeys.analysisSummary: 'Summary',
  StringKeys.analysisCredibilityScore: 'Credibility score',
  StringKeys.analysisVerifiability: 'Verifiability',
  StringKeys.analysisTitle: 'Analysis',
  StringKeys.analysisSubtitle:
      'Paste a claim, article, or headline — ANNEX scores its credibility and explains why.',
  StringKeys.analysisInputHint: 'Paste a claim, article, or headline…',

  // auth
  StringKeys.authSignIn: 'Sign in to verify what you read.',
  StringKeys.authSignInTab: 'Sign in',
  StringKeys.authSignUp: 'Create your ANNEX account',
  StringKeys.authSignOut: 'Sign out',
  StringKeys.authEmail: 'Email',
  StringKeys.authPassword: 'Password',
  StringKeys.authConfirmPassword: 'Confirm password',
  StringKeys.authOrContinue: 'or continue with',
  StringKeys.authCreateAccount: 'Create account',
  StringKeys.authHaveAccount: 'Already have an account? Sign in',
  StringKeys.authInvalidEmail: 'Enter a valid email address.',
  StringKeys.authPasswordTooShort: 'Password must be at least 8 characters.',
  StringKeys.authPasswordTooWeak: 'Use at least one letter and one number.',
  StringKeys.authPasswordsDontMatch: 'Passwords do not match.',
  StringKeys.authContinueGuest: 'Continue as guest',
  StringKeys.authContinueGoogle: 'Continue with Google',
  StringKeys.authGuestLabel: 'Guest',
  StringKeys.authPrivacyNote:
      'By continuing you agree to use ANNEX responsibly. Your analyses are stored in your private account.',
  StringKeys.authFeatureAnalyze: 'Verify claims, headlines & images with AI',
  StringKeys.authFeatureSources: 'Check the credibility of news sources',
  StringKeys.authFeatureLessons: 'Learn media literacy in minutes',
  StringKeys.authErrorWrongPassword: 'Incorrect password. Try again.',
  StringKeys.authErrorUserNotFound: 'No account found for this email.',
  StringKeys.authErrorEmailInUse: 'An account with this email already exists.',
  StringKeys.authErrorWeakPassword: 'Password is too weak. Use at least 8 characters.',
  StringKeys.authErrorInvalidCredential: 'Invalid email or password.',
  StringKeys.authErrorTooManyRequests: 'Too many attempts. Try again in a moment.',
  StringKeys.authErrorNetwork: 'Network error. Check your connection.',
  StringKeys.authErrorDefault: 'Sign-in failed. Please try again.',

  // analysis input modes (image analysis)
  StringKeys.analysisModeText: 'Text',
  StringKeys.analysisModeImage: 'Image',
  StringKeys.analysisImageHint:
      'Upload a screenshot or photo — ANNEX reads the text and checks for tampering.',
  StringKeys.analysisImageChoose: 'Choose image',
  StringKeys.analysisImageChange: 'Change image',
  StringKeys.analysisImageSubmit: 'Analyze image',
  StringKeys.analysisImageOcr: 'Text extracted from the image',
  StringKeys.analysisImageForensics: 'Image forensics',
  StringKeys.analysisImageRisk: 'Tamper risk',
  StringKeys.analysisImageSignals: 'Signals',
  StringKeys.analysisImageDimensions: 'Dimensions',

  // lessons
  StringKeys.lessonsTitle: 'Lessons',
  StringKeys.lessonsSubtitle: 'Build your media literacy, one short lesson at a time.',
  StringKeys.lessonsComplete: 'Mark complete',
  StringKeys.lessonsCompleted: 'Completed',
  StringKeys.lessonsMinutes: '{minutes} min',
  StringKeys.lessonsDifficulty: 'Difficulty',
  StringKeys.lessonsDifficultyBeginner: 'Beginner',
  StringKeys.lessonsDifficultyIntermediate: 'Intermediate',
  StringKeys.lessonsDifficultyAdvanced: 'Advanced',
  StringKeys.lessonsEmpty: 'No lessons available yet.',
  StringKeys.lessonsError: 'Could not load lessons.',

  // classes
  StringKeys.classesTitle: 'Classes',
  StringKeys.classesSubtitle: 'Create a class, invite students, and track progress.',
  StringKeys.classesCreate: 'Create class',
  StringKeys.classesJoin: 'Join class',
  StringKeys.classesInviteCode: 'Invite code',
  StringKeys.classesName: 'Class name',
  StringKeys.classesDescription: 'Description',
  StringKeys.classesMembers: 'Members',
  StringKeys.classesAssignments: 'Assignments',
  StringKeys.classesAssignLesson: 'Assign lesson',
  StringKeys.classesProgress: 'Progress',
  StringKeys.classesRoleTeacher: 'Teacher',
  StringKeys.classesRoleStudent: 'Student',
  StringKeys.classesEmpty: 'No classes yet. Create one or join with a code.',
  StringKeys.classesError: 'Could not load classes.',
  StringKeys.classesCompletedCount: '{completed}/{total} completed',
  StringKeys.classesDeleteClass: 'Delete class',
  StringKeys.classesRemoveMember: 'Remove member',
  StringKeys.classesRemoveAssignment: 'Remove assignment',
  StringKeys.classesStudents: 'Students',
  StringKeys.classesNoAssignments: 'No lessons assigned yet.',
  StringKeys.classesNoMembers: 'No students have joined yet.',
  StringKeys.classesDue: 'Due {date}',
  StringKeys.classesClassId: 'Class ID',
  StringKeys.classesJoinHint: 'Enter the class ID and invite code from your teacher.',
  StringKeys.classesCreateSuccess:
      'Class created. Share the invite code with your students.',

  // suggestions
  StringKeys.suggestionsTitle: 'Contribute',
  StringKeys.suggestionsSubtitle: 'Help translate ANNEX into more languages.',
  StringKeys.suggestionsMissing: 'Untranslated keys',
  StringKeys.suggestionsPropose: 'Propose translation',
  StringKeys.suggestionsYourSubmissions: 'Your submissions',
  StringKeys.suggestionsEmpty: 'No untranslated keys — this language is complete.',
  StringKeys.suggestionsError: 'Could not load translation suggestions.',
  StringKeys.suggestionsNoSubmissions:
      'You have not submitted any translations yet.',
  StringKeys.suggestionsValue: 'Your translation',
  StringKeys.suggestionsEnglish: 'English',
  StringKeys.suggestionsStatusPending: 'Pending review',
  StringKeys.suggestionsStatusApproved: 'Approved',
  StringKeys.suggestionsStatusRejected: 'Rejected',
  StringKeys.suggestionsSubmitted: 'Submitted for review.',
  StringKeys.suggestionsLocale: 'Language',
  StringKeys.suggestionsContributorNote:
      'Help translate ANNEX into your language.',
  StringKeys.suggestionsReviewQueue: 'Review queue',
  StringKeys.suggestionsApprove: 'Approve',
  StringKeys.suggestionsReject: 'Reject',
  StringKeys.suggestionsNoPending: 'No suggestions waiting for review.',

  // sources
  StringKeys.sourcesTitle: 'Sources',
  StringKeys.sourcesSubtitle: 'Search publishers and domains for their credibility profile.',
  StringKeys.sourcesSearchHint: 'Search publishers or domains…',
  StringKeys.sourcesSearch: 'Search',
  StringKeys.sourcesModelScore: 'Model score',
  StringKeys.sourcesCommunity: 'Community',
  StringKeys.sourcesRate: 'Rate this source',
  StringKeys.sourcesYourRating: 'Your rating',
  StringKeys.sourcesNoResults: 'No sources found.',
  StringKeys.sourcesError: 'Could not load sources.',
  StringKeys.sourcesTrustSignals: 'Trust signals',
  StringKeys.sourcesRatingsCount: '{count} ratings',
  StringKeys.sourcesAverage: '{average} avg',
  StringKeys.sourcesScoreLabel: 'Credibility score',
  StringKeys.sourcesCommunityEmpty: 'No community ratings yet.',
  StringKeys.sourcesOpenProfile: 'View profile',

  // settings
  StringKeys.settingsTitle: 'Settings',
  StringKeys.settingsSubtitle: 'Language, appearance, and account.',
  StringKeys.settingsLanguage: 'Language',
  StringKeys.settingsTheme: 'Appearance',
  StringKeys.settingsThemeSystem: 'System',
  StringKeys.settingsThemeLight: 'Light',
  StringKeys.settingsThemeDark: 'Dark',
  StringKeys.settingsAccount: 'Account',

  // errors
  StringKeys.errorsGeneric: 'Something went wrong. Please try again.',
  StringKeys.errorsNotFound: 'Not found.',
  StringKeys.errorsRateLimited: 'Too many requests. Try again shortly.',
};
