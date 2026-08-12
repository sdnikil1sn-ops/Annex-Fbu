/**
 * Backend API client for the extension (Phase 10).
 *
 * The extension talks to the same v1 API as the Flutter apps: analysis
 * submission + polling, locale registry, and versioned bundles. All
 * requests authenticate with the user's ANNEX session when signed in.
 */
import { Analysis } from './analysis';
import { LocaleInfo, TranslationBundle } from './i18n';

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface ApiClient {
  submitText(text: string, locale: string): Promise<Analysis>;
  fetchAnalysis(id: string): Promise<Analysis>;
  fetchLocales(): Promise<LocaleInfo[]>;
  fetchBundle(locale: string): Promise<TranslationBundle>;
}

/** Resolves the bearer token for the current session, or null. */
export type TokenProvider = () => Promise<string | null>;

/** Fetch-based client against the ANNEX v1 API. */
export class HttpApiClient implements ApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly tokenProvider: TokenProvider,
  ) {}

  async submitText(text: string, locale: string): Promise<Analysis> {
    const data = await this.post('/analysis', { input_type: 'text', text, locale });
    return data.data as Analysis;
  }

  async fetchAnalysis(id: string): Promise<Analysis> {
    const data = await this.get(`/analysis/${id}`);
    return data.data as Analysis;
  }

  async fetchLocales(): Promise<LocaleInfo[]> {
    const data = await this.get('/i18n/locales');
    const payload = data.data as { locales?: LocaleInfo[] };
    return payload.locales ?? [];
  }

  async fetchBundle(locale: string): Promise<TranslationBundle> {
    const data = await this.get(`/i18n/bundles/${encodeURIComponent(locale)}`);
    return data.data as TranslationBundle;
  }

  private async get(path: string): Promise<{ data: unknown }> {
    return this.request(path, { method: 'GET' });
  }

  private async post(path: string, body: unknown): Promise<{ data: unknown }> {
    return this.request(path, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  private async request(path: string, init: RequestInit): Promise<{ data: unknown }> {
    const token = await this.tokenProvider();
    const headers: Record<string, string> = {
      accept: 'application/json',
      ...(init.headers as Record<string, string> | undefined),
    };
    if (token) headers.authorization = `Bearer ${token}`;

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    } catch {
      throw new ApiError('network.error', 'Cannot reach the ANNEX backend.');
    }

    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError('api.invalid_response', 'The backend returned invalid JSON.');
    }

    if (!response.ok) {
      const error = (body as { error?: { code?: string; message?: string } })?.error;
      throw new ApiError(
        error?.code ?? 'api.error',
        error?.message ?? `Request failed (${response.status})`,
      );
    }
    return body as { data: unknown };
  }
}
