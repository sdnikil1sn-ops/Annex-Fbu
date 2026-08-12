import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react';
import { chromeMock } from './setup';
import { PopupApp } from '../src/popup/PopupApp';
import { Analysis, AnalysisReport } from '../src/shared/analysis';
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

const completed: Analysis = {
  id: 'an-1',
  input_type: 'text',
  status: 'completed',
  locale: 'en',
  failure_reason: null,
  report: {
    summary: 'Mostly verifiable.',
    claims: [
      { text: 'The earth is round', verifiability: 0.9 },
      { text: 'Waves exist', verifiability: 0.4 },
    ],
  } satisfies AnalysisReport,
  created_at: '2026-08-12T00:00:00Z',
  completed_at: '2026-08-12T00:00:01Z',
};

/** Queue canned responses for chrome.runtime.sendMessage by message type. */
function mockSendMessage(routes: Record<string, unknown>) {
  chromeMock.runtime.sendMessage.mockImplementation(
    (message: { type: string }, callback: (response: unknown) => void) => {
      const data = routes[message.type];
      if (data === undefined) {
        callback({ ok: false, error: { code: 'test.missing', message: 'no route' } });
      } else if (typeof data === 'object' && data !== null && 'ok' in data) {
        callback(data as { ok: boolean });
      } else {
        callback({ ok: true, data });
      }
    },
  );
}

function mockSelection(text: string) {
  // MV3 APIs are promise-based; resolve the tab list asynchronously.
  chromeMock.tabs.query.mockResolvedValue([{ id: 7 }]);
  chromeMock.tabs.sendMessage.mockResolvedValue({ text });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('PopupApp', () => {
  it('renders the submit UI with the bundle strings', async () => {
    mockSendMessage({
      'get-locales': [{ code: 'en', fallback_code: null }],
      'get-bundle': bundle,
      'get-account': null,
    });
    mockSelection('');
    render(<PopupApp />);
    expect(await screen.findByPlaceholderText('Paste or select text…')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Analyze' })).toBeDisabled();
  });

  it('prefills the text area from the page selection', async () => {
    mockSendMessage({
      'get-locales': [{ code: 'en', fallback_code: null }],
      'get-bundle': bundle,
      'get-account': null,
    });
    mockSelection('selected sentence from the page');
    render(<PopupApp />);
    const textarea = (await screen.findByPlaceholderText(
      'Paste or select text…',
    )) as HTMLTextAreaElement;
    expect(textarea.value).toBe('selected sentence from the page');
  });

  it('submits, polls, and renders the terminal report', async () => {
    mockSendMessage({
      'get-locales': [{ code: 'en', fallback_code: null }],
      'get-bundle': bundle,
      'get-account': null,
      verify: { ...completed, status: 'pending' },
      'fetch-analysis': completed,
    });
    mockSelection('');
    render(<PopupApp />);

    const textarea = await screen.findByPlaceholderText('Paste or select text…');
    fireEvent.change(textarea, { target: { value: 'The earth is round and waves exist.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    // Enable fake timers after the click (findBy* needs real timers).
    // Each advance is its own act() so React flushes between timer steps:
    // t=0 lets the verify microtask register the poll interval, the next
    // steps fire it and let the async fetch resolve before re-rendering.
    vi.useFakeTimers();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    vi.useRealTimers();

    expect(await screen.findByText('Credibility score')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('65%')).toBeInTheDocument());
    expect(screen.getByText('Mostly verifiable.')).toBeInTheDocument();
  });

  it('shows a retry affordance when the backend errors', async () => {
    mockSendMessage({
      'get-locales': [{ code: 'en', fallback_code: null }],
      'get-bundle': bundle,
      'get-account': null,
      verify: { ok: false, error: { code: 'analysis.submit_failed', message: 'boom' } },
    });
    mockSelection('');
    render(<PopupApp />);

    const textarea = await screen.findByPlaceholderText('Paste or select text…');
    fireEvent.change(textarea, { target: { value: 'some text' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyze' }));

    expect(await screen.findByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });
});
