/**
 * Explicit in-memory mock of [ApiClient] for tests and local dev.
 *
 * Mirrors the mobile app's MockAnalysisApi: submissions start `pending`,
 * then complete with a deterministic report (or fail on a trigger
 * substring) — no network required.
 */
import { Analysis, AnalysisReport } from './analysis';
import { ApiClient } from './api';
import { LocaleInfo, TranslationBundle } from './i18n';

export class MockApiClient implements ApiClient {
  constructor(
    private readonly failTrigger = '!!!',
    private readonly delayMs = 0,
  ) {}

  private readonly analyses: Analysis[] = [];
  private readonly inputs: string[] = [];
  private nextId = 1;
  lastSubmittedText: string | null = null;

  private readonly report: AnalysisReport = {
    summary: 'The text makes two checkable claims with verifiable evidence.',
    claims: [
      { text: 'The Earth orbits the Sun', verifiability: 0.95 },
      { text: 'The claim cites an outdated study', verifiability: 0.45 },
    ],
  };

  async submitText(text: string, locale: string): Promise<Analysis> {
    this.lastSubmittedText = text;
    await this.delay();
    const now = new Date().toISOString();
    const analysis: Analysis = {
      id: `mock-${this.nextId++}`,
      input_type: 'text',
      status: 'pending',
      locale,
      failure_reason: null,
      report: null,
      created_at: now,
      completed_at: null,
    };
    this.analyses.push(analysis);
    this.inputs.push(text);
    return analysis;
  }

  async fetchAnalysis(id: string): Promise<Analysis> {
    await this.delay();
    const index = this.analyses.findIndex((a) => a.id === id);
    if (index < 0) {
      throw new Error('analysis.not_found: Analysis not found');
    }
    const current = this.analyses[index]!;
    if (isTerminal(current.status)) return current;

    const failed = this.inputs[index]!.includes(this.failTrigger);
    const updated: Analysis = failed
      ? {
          ...current,
          status: 'failed',
          failure_reason: 'analysis.processing_failed',
          completed_at: new Date().toISOString(),
        }
      : {
          ...current,
          status: 'completed',
          report: this.report,
          completed_at: new Date().toISOString(),
        };
    this.analyses[index] = updated;
    return updated;
  }

  async fetchLocales(): Promise<LocaleInfo[]> {
    await this.delay();
    return [
      { code: 'en', fallback_code: null },
      { code: 'pt', fallback_code: 'en' },
      { code: 'es', fallback_code: 'en' },
    ];
  }

  async fetchBundle(locale: string): Promise<TranslationBundle> {
    await this.delay();
    const shared: Record<string, { value: string; plural: string }> = {
      'common.cancel': { value: 'Cancel', plural: 'none' },
      'common.retry': { value: 'Retry', plural: 'none' },
      'common.learn_before_you_believe': {
        value: 'Learn before you believe.',
        plural: 'none',
      },
      'analysis.title': { value: 'Verify', plural: 'none' },
      'analysis.submit': { value: 'Analyze text', plural: 'none' },
      'analysis.summary': { value: 'Summary', plural: 'none' },
      'analysis.credibility_score': { value: 'Credibility score', plural: 'none' },
      'analysis.verifiability': { value: 'Verifiability', plural: 'none' },
      'settings.title': { value: 'Options', plural: 'none' },
      'settings.api': { value: 'API', plural: 'none' },
      'settings.api_base_url': { value: 'Base URL', plural: 'none' },
      'auth.sign_in': { value: 'Sign in', plural: 'none' },
      'auth.sign_out': { value: 'Sign out', plural: 'none' },
      'auth.signed_in': { value: 'Signed in', plural: 'none' },
      'auth.continue_google': { value: 'Sign in with Google', plural: 'none' },
      'errors.generic': { value: 'Something went wrong. Please try again.', plural: 'none' },
    };
    if (locale === 'en') {
      return { locale: 'en', fallback_locale: null, version: 1, entries: shared };
    }
    return {
      locale,
      fallback_locale: 'en',
      version: 1,
      entries: { ...shared, 'common.cancel': { value: 'Cancelar', plural: 'none' } },
    };
  }

  private async delay(): Promise<void> {
    if (this.delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.delayMs));
    }
  }
}

function isTerminal(status: Analysis['status']): boolean {
  return status === 'completed' || status === 'failed';
}
