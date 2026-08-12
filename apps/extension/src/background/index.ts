/**
 * Background service worker (Phase 10).
 *
 * Owns the browser-facing capabilities: the "Verify with ANNEX" context
 * menu, the typed message router between contexts, and the backend API
 * calls (analysis submission + polling, locale/bundle fetches). Content
 * and popup never talk to the network directly — they message us.
 *
 * Composition: Firebase Auth is used when the build provides
 * `VITE_FIREBASE_*` configuration (never shipped in a bundle without a
 * project), otherwise the explicit mock keeps local dev/test working.
 * The API client reads the stored base URL and authenticates with the
 * user's ID token; dev builds fall back to the mock API when no backend
 * is reachable.
 */
import { HttpApiClient } from '../shared/api';
import { AuthGateway, FirebaseAuthGateway, MockAuthGateway } from '../shared/auth';
import { MockApiClient } from '../shared/mock_api';
import { failure, RequestMessage, success, VerifyRequest } from '../shared/contracts';

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

/** Build-time Firebase config; empty unless provided to the build. */
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY as string | undefined,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN as string | undefined,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID as string | undefined,
  appId: import.meta.env.VITE_FIREBASE_APP_ID as string | undefined,
};
const firebaseValues = Object.values(firebaseConfig);
const hasFirebaseConfig = firebaseValues.every(Boolean);
if (!hasFirebaseConfig && firebaseValues.some(Boolean)) {
  // Partial configuration means a misconfigured build — surface it instead
  // of silently failing closed at runtime.
  console.warn('[annex] Incomplete VITE_FIREBASE_* configuration; sign-in disabled.');
}

export interface BackgroundDeps {
  api: ApiClientLike;
  auth: AuthGateway;
  localesCache: Map<string, LocaleRecord[]>;
}

interface LocaleRecord {
  code: string;
  fallback_code?: string | null;
}

/** Minimal surface the router needs (loosened for the dev mock). */
export interface ApiClientLike {
  submitText(text: string, locale: string): Promise<{ id: string; status: string }>;
  fetchAnalysis(id: string): Promise<{ id: string; status: string }>;
  fetchLocales(): Promise<LocaleRecord[]>;
  fetchBundle(locale: string): Promise<unknown>;
}

/**
 * Verify a selection end-to-end: submit, then return the analysis so the
 * caller can poll with fetch-analysis.
 */
export async function handleRequest(
  message: RequestMessage,
  deps: BackgroundDeps,
): Promise<ReturnType<typeof success | typeof failure>> {
  // A malformed message must never leave the caller's sendMessage promise
  // hanging: respond with a structured error instead of throwing (an
  // unhandled throw skips sendResponse and the sender never settles).
  // Every message type carries a plain-object payload (bridge.ts always
  // sends `{}` even for payload-less messages), so rejecting anything
  // that is not a plain object covers null/undefined, primitives, and
  // arrays alike.
  if (
    !message ||
    message.payload === null ||
    typeof message.payload !== 'object' ||
    Array.isArray(message.payload)
  ) {
    return failure('contracts.missing_payload', 'Message is missing its payload.');
  }
  switch (message.type) {
    case 'verify': {
      const { text, locale } = message.payload as VerifyRequest;
      if (!text.trim()) return failure('validation.empty_text', 'Nothing to verify.');
      try {
        const analysis = await deps.api.submitText(text.trim(), locale);
        return success(analysis);
      } catch (error) {
        return failure('analysis.submit_failed', messageOf(error));
      }
    }

    case 'fetch-analysis': {
      const { id } = message.payload as { id: string };
      try {
        return success(await deps.api.fetchAnalysis(id));
      } catch (error) {
        return failure('analysis.fetch_failed', messageOf(error));
      }
    }

    case 'get-locales': {
      try {
        const locales = await deps.api.fetchLocales();
        deps.localesCache.set('all', locales);
        return success(locales);
      } catch (error) {
        return failure('i18n.locales_failed', messageOf(error));
      }
    }

    case 'get-bundle': {
      const { locale } = message.payload as { locale: string };
      try {
        return success(await deps.api.fetchBundle(locale));
      } catch (error) {
        return failure('i18n.bundle_failed', messageOf(error));
      }
    }

    case 'get-account':
      return success(await deps.auth.currentUser());

    case 'sign-in':
      try {
        return success(await deps.auth.signInWithGoogle());
      } catch (error) {
        return failure('auth.sign_in_failed', messageOf(error));
      }

    case 'sign-out':
      try {
        await deps.auth.signOut();
        return success(null);
      } catch (error) {
        return failure('auth.sign_out_failed', messageOf(error));
      }

    default:
      return failure('contracts.unknown_message', `Unhandled message: ${message.type}`);
  }
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/* ------------------------------------------------------------------ */
/* Browser wiring                                                      */
/* ------------------------------------------------------------------ */

/** Build the composition root from build-time config + stored settings. */
async function buildDeps(): Promise<BackgroundDeps> {
  const isDev = import.meta.env.DEV;

  // Firebase only when configured at build time; the mock only in dev
  // builds — production without a Firebase project fails closed.
  const auth: AuthGateway = hasFirebaseConfig
    ? new FirebaseAuthGateway(
        firebaseConfig as {
          apiKey: string;
          authDomain: string;
          projectId: string;
          appId: string;
        },
      )
    : isDev
      ? new MockAuthGateway()
      : new UnavailableAuthGateway();

  const stored = (await chrome.storage.sync.get('apiBaseUrl').catch(() => ({}))) as {
    apiBaseUrl?: string;
  };
  const baseUrl = stored.apiBaseUrl || DEFAULT_API_BASE_URL;

  // Dev builds fall back to the mock API when no backend is configured;
  // production builds always talk to the configured endpoint.
  const api: ApiClientLike =
    isDev && !stored.apiBaseUrl
      ? new MockApiClient()
      : new HttpApiClient(baseUrl, () => auth.idToken());

  return { api, auth, localesCache: new Map() };
}

/** Auth gateway for production builds without Firebase configuration. */
class UnavailableAuthGateway implements AuthGateway {
  async currentUser(): Promise<null> {
    return null;
  }

  async idToken(): Promise<null> {
    return null;
  }

  async signInWithGoogle(): Promise<never> {
    throw new Error('auth.not_configured: ANNEX extension is not configured for sign-in');
  }

  async signOut(): Promise<void> {
    // Nothing to sign out of.
  }
}

/** Register all browser handlers (context menu, typed message router). */
export function setupBrowserExtension(deps: BackgroundDeps): void {
  // Context menu: verify the selected text.
  chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
      id: 'annex-verify-selection',
      title: 'Verify with ANNEX',
      contexts: ['selection'],
    });
  });

  chrome.contextMenus.onClicked.addListener((info) => {
    if (info.menuItemId !== 'annex-verify-selection' || !info.selectionText) return;
    // Ask the content script to mark the selection on the page; the popup
    // (opened separately) drives the verification flow.
    void chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab?.id) return;
      void chrome.tabs.sendMessage(tab.id, {
        type: 'annex:selection',
        text: info.selectionText,
      });
    });
  });

  // Typed message router: every context talks to the background.
  chrome.runtime.onMessage.addListener((message: RequestMessage, _sender, sendResponse) => {
    void handleRequest(message, deps).then(sendResponse);
    return true; // asynchronous response
  });
}

/** Service-worker entry: wire deps and register browser handlers. */
export function init(): void {
  void buildDeps().then((deps) => setupBrowserExtension(deps));
}

// Self-start when loaded as the MV3 service worker (or imported by tests,
// where init() is intentionally not called so tests stay deterministic).
if (!import.meta.env.VITEST) {
  init();
}
