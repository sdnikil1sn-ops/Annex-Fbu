import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { chromeMock } from './setup';
import { PopupApp, getSelection } from '../src/popup/PopupApp';
import { TranslationBundle } from '../src/shared/i18n';

const bundle: TranslationBundle = {
  locale: 'en',
  fallback_locale: null,
  version: 1,
  entries: {
    'analysis.submit': { value: 'Analyze', plural: 'none' },
    'analysis.credibility_score': { value: 'Credibility score', plural: 'none' },
    'analysis.input_hint': { value: 'Paste or select text…', plural: 'none' },
    'common.retry': { value: 'Retry', plural: 'none' },
    'common.loading': { value: 'Loading…', plural: 'none' },
  },
};

/** No selection on the page: tabs.query resolves empty, so getSelection() returns ''. */
function mockNoSelection() {
  chromeMock.tabs.query.mockResolvedValue([]);
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('popup getSelection', () => {
  it('unwraps the selection envelope from the content script', async () => {
    chromeMock.tabs.query.mockResolvedValue([{ id: 7, url: 'http://example.com/' }]);
    chromeMock.tabs.sendMessage.mockResolvedValue({ ok: true, data: { text: 'selected words' } });

    await expect(getSelection()).resolves.toBe('selected words');
    expect(chromeMock.tabs.sendMessage).toHaveBeenCalledWith(7, {
      type: 'annex:get-selection',
    });
  });

  it('returns an empty string when the content script reports failure', async () => {
    chromeMock.tabs.query.mockResolvedValue([{ id: 7 }]);
    chromeMock.tabs.sendMessage.mockResolvedValue({
      ok: false,
      error: { code: 'content.highlight_failed', message: 'nope' },
    });

    await expect(getSelection()).resolves.toBe('');
  });

  it('returns an empty string when no tab is available', async () => {
    chromeMock.tabs.query.mockResolvedValue([]);

    await expect(getSelection()).resolves.toBe('');
  });
});

describe('PopupApp retry flow', () => {
  it('shows a retry affordance when verify fails, and retry re-submits', async () => {
    // First verify call fails; the retry's second call succeeds with a
    // terminal analysis so the flow completes.
    let calls = 0;
    chromeMock.runtime.sendMessage.mockImplementation(
      (message: { type: string }, callback: (response: unknown) => void) => {
        switch (message.type) {
          case 'get-locales':
            callback({ ok: true, data: [{ code: 'en', fallback_code: null }] });
            return;
          case 'get-bundle':
            callback({ ok: true, data: bundle });
            return;
          case 'get-account':
            callback({ ok: true, data: null });
            return;
          case 'verify':
            calls += 1;
            if (calls === 1) {
              callback({ ok: false, error: { code: 'analysis.submit_failed', message: 'boom' } });
            } else {
              callback({
                ok: true,
                data: {
                  id: 'an-1',
                  input_type: 'text',
                  status: 'completed',
                  locale: 'en',
                  failure_reason: null,
                  report: {
                    summary: 'Mostly verifiable.',
                    claims: [{ text: 'The earth is round', verifiability: 0.9 }],
                  },
                  created_at: '2026-08-12T00:00:00Z',
                  completed_at: '2026-08-12T00:00:01Z',
                },
              });
            }
            return;
          default:
            callback({ ok: false, error: { code: 'test.missing', message: 'no route' } });
        }
      },
    );
    mockNoSelection();
    render(<PopupApp />);

    const textarea = await screen.findByPlaceholderText('Paste or select text…');
    fireEvent.change(textarea, { target: { value: 'The earth is round.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    // First submit fails → the retry affordance renders (real timers: the
    // verify promise resolves on the next microtask flush).
    const retry = await screen.findByRole('button', { name: 'Retry' });
    expect(retry).toBeInTheDocument();

    // Retry re-submits; the second call is terminal, so the report renders.
    fireEvent.click(retry);
    await waitFor(() => expect(screen.getByText('Credibility score')).toBeInTheDocument());
    expect(screen.getByText('Mostly verifiable.')).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
