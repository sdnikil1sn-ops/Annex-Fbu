import { describe, expect, it, vi } from 'vitest';
import { handleRequest, BackgroundDeps, setupBrowserExtension } from '../src/background/index';
import { chromeMock, contextMenusEvent } from './setup';
import { Analysis } from '../src/shared/analysis';
import { ApiClient } from '../src/shared/api';
import { AuthGateway } from '../src/shared/auth';
import { RequestMessage } from '../src/shared/contracts';

const terminal: Analysis = {
  id: 'a1',
  input_type: 'text',
  status: 'completed',
  locale: 'en',
  failure_reason: null,
  report: { summary: 'ok', claims: [{ text: 'c', verifiability: 1 }] },
  created_at: '2026-08-12T00:00:00Z',
  completed_at: '2026-08-12T00:00:01Z',
};

function makeDeps(overrides: Partial<BackgroundDeps> = {}): BackgroundDeps {
  const api: ApiClient = {
    submitText: vi.fn(async () => terminal),
    fetchAnalysis: vi.fn(async () => terminal),
    fetchLocales: vi.fn(async () => []),
    fetchBundle: vi.fn(async () => ({
      locale: 'en',
      fallback_locale: null,
      version: 1,
      entries: {},
    })),
  };
  const auth: AuthGateway = {
    currentUser: vi.fn(async () => null),
    idToken: vi.fn(async () => null),
    signInWithGoogle: vi.fn(async () => ({ uid: 'u1', email: 'a@b.c', displayName: null })),
    signOut: vi.fn(async () => undefined),
  };
  return { api, auth, localesCache: new Map(), ...overrides };
}

function message(type: RequestMessage['type'], payload: unknown): RequestMessage {
  return { type, requestId: 'test-1', payload };
}

describe('handleRequest', () => {
  it('verifies text end-to-end', async () => {
    const deps = makeDeps();
    const response = await handleRequest(
      message('verify', { text: '  claim text  ', locale: 'en' }),
      deps,
    );
    expect(response.ok).toBe(true);
    if (response.ok) expect(response.data).toEqual(terminal);
    expect(deps.api.submitText).toHaveBeenCalledWith('claim text', 'en');
  });

  it('rejects empty text with a validation failure', async () => {
    const deps = makeDeps();
    const response = await handleRequest(message('verify', { text: '   ', locale: 'en' }), deps);
    expect(response.ok).toBe(false);
    if (!response.ok) {
      expect(response.error.code).toBe('validation.empty_text');
      expect(deps.api.submitText).not.toHaveBeenCalled();
    }
  });

  it('maps provider failures to a structured error', async () => {
    const deps = makeDeps({
      api: {
        ...makeDeps().api,
        submitText: vi.fn(async () => {
          throw new Error('boom');
        }),
      },
    });
    const response = await handleRequest(message('verify', { text: 'x', locale: 'en' }), deps);
    expect(response.ok).toBe(false);
    if (!response.ok) expect(response.error.code).toBe('analysis.submit_failed');
  });

  it('fetches a single analysis for polling', async () => {
    const deps = makeDeps();
    const response = await handleRequest(message('fetch-analysis', { id: 'a1' }), deps);
    expect(response.ok).toBe(true);
    expect(deps.api.fetchAnalysis).toHaveBeenCalledWith('a1');
  });

  it('caches the locale registry after fetching it', async () => {
    const deps = makeDeps();
    await handleRequest(message('get-locales', {}), deps);
    expect(deps.localesCache.get('all')).toEqual([]);
  });

  it('returns the current account', async () => {
    const deps = makeDeps();
    const response = await handleRequest(message('get-account', {}), deps);
    expect(response.ok).toBe(true);
    if (response.ok) expect(response.data).toBeNull();
  });

  it('rejects unknown message types', async () => {
    const deps = makeDeps();
    const response = await handleRequest(message('nope' as RequestMessage['type'], {}), deps);
    expect(response.ok).toBe(false);
    if (!response.ok) expect(response.error.code).toBe('contracts.unknown_message');
  });
});

describe('setupBrowserExtension', () => {
  it('registers the verify context menu on install', () => {
    setupBrowserExtension(makeDeps());
    chromeMock.runtime.onInstalled._emit();
    expect(chromeMock.contextMenus.create).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'annex-verify-selection', contexts: ['selection'] }),
    );
  });

  it('forwards a context-menu selection to the active tab', () => {
    setupBrowserExtension(makeDeps());
    chromeMock.tabs.query.mockImplementation(
      (_query: unknown, callback: (tabs: unknown[]) => void) => {
        callback([{ id: 42 }]);
      },
    );
    chromeMock.tabs.sendMessage.mockResolvedValue({ ok: true });

    contextMenusEvent._emit({
      menuItemId: 'annex-verify-selection',
      selectionText: 'claim to check',
    });

    expect(chromeMock.tabs.query).toHaveBeenCalled();
    expect(chromeMock.tabs.sendMessage).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ type: 'annex:selection', text: 'claim to check' }),
    );
  });

  it('ignores clicks on other menu items', () => {
    setupBrowserExtension(makeDeps());
    chromeMock.tabs.query.mockClear();
    contextMenusEvent._emit({ menuItemId: 'other-menu', selectionText: 'x' });
    expect(chromeMock.tabs.query).not.toHaveBeenCalled();
  });
});
