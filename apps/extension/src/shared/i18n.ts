/**
 * Runtime i18n (ADR-0007) — typed keys + fallback-chain resolution.
 *
 * The extension loads versioned bundles from the ANNEX backend exactly
 * like the Flutter apps. Keys are typed constants (the TS mirror of the
 * `shared_utils` Dart registry) so UI code never inlines string keys.
 */
export interface BundleEntry {
  value: string;
  plural: string;
}

export interface TranslationBundle {
  locale: string;
  fallback_locale: string | null;
  version: number;
  entries: Record<string, BundleEntry>;
}

/** Typed string keys — mirror of `packages/shared_utils` StringKeys. */
export const StringKeys = {
  commonCancel: 'common.cancel',
  commonSave: 'common.save',
  commonRetry: 'common.retry',
  commonLoading: 'common.loading',
  commonClose: 'common.close',
  commonLearnBeforeYouBelieve: 'common.learn_before_you_believe',
  commonClaimsCount: 'common.claims_count',
  analysisSubmit: 'analysis.submit',
  analysisPending: 'analysis.pending',
  analysisProcessing: 'analysis.processing',
  analysisCompleted: 'analysis.completed',
  analysisFailed: 'analysis.failed',
  analysisSummary: 'analysis.summary',
  analysisCredibilityScore: 'analysis.credibility_score',
  analysisVerifiability: 'analysis.verifiability',
  analysisTitle: 'analysis.title',
  analysisInputHint: 'analysis.input_hint',
  authSignIn: 'auth.sign_in',
  authSignOut: 'auth.sign_out',
  authContinueGuest: 'auth.continue_guest',
  authContinueGoogle: 'auth.continue_google',
  authGuestLabel: 'auth.guest_label',
  settingsTitle: 'settings.title',
  settingsLanguage: 'settings.language',
  settingsTheme: 'settings.theme',
  settingsThemeSystem: 'settings.theme_system',
  settingsThemeLight: 'settings.theme_light',
  settingsThemeDark: 'settings.theme_dark',
  settingsAccount: 'settings.account',
  settingsApi: 'settings.api',
  settingsApiBaseUrl: 'settings.api_base_url',
  authSignedIn: 'auth.signed_in',
  errorsGeneric: 'errors.generic',
  errorsNotFound: 'errors.not_found',
  errorsRateLimited: 'errors.rate_limited',
} as const;

export type StringKey = (typeof StringKeys)[keyof typeof StringKeys];

/** Locale registry from `GET /v1/i18n/locales`. */
export interface LocaleInfo {
  code: string;
  fallback_code: string | null;
}

/**
 * Resolve the fallback chain for a locale: requested → parent → … →
 * default (mirrors the backend algorithm and `shared_utils`).
 */
export function resolveFallbackChain(
  locale: string,
  locales: Map<string, string | null>,
  defaultLocale: string,
): string[] {
  const chain: string[] = [];
  const seen = new Set<string>();
  let current: string | null = locale;
  while (current !== null && !seen.has(current)) {
    seen.add(current);
    chain.push(current);
    const fallback = locales.get(current);
    current = fallback === undefined ? null : fallback;
  }
  if (chain[chain.length - 1] !== defaultLocale) {
    chain.push(defaultLocale);
  }
  return chain;
}

/**
 * Translate a typed key against a resolved bundle; falls back to the key
 * itself when absent so missing translations never render raw.
 */
export function translate(key: StringKey | string, bundle: TranslationBundle): string {
  return bundle.entries[key]?.value ?? key;
}
