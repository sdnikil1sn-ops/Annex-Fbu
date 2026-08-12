import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { chromeMock } from './setup';
import { OptionsApp } from '../src/options/OptionsApp';
import { TranslationBundle } from '../src/shared/i18n';

const bundle: TranslationBundle = {
  locale: 'en',
  fallback_locale: null,
  version: 1,
  entries: {
    'settings.title': { value: 'Settings', plural: 'none' },
    'settings.language': { value: 'Language', plural: 'none' },
    'settings.api': { value: 'API', plural: 'none' },
    'settings.api_base_url': { value: 'Base URL', plural: 'none' },
    'settings.account': { value: 'Account', plural: 'none' },
    'auth.signed_in': { value: 'Signed in', plural: 'none' },
    'auth.continue_google': { value: 'Continue with Google', plural: 'none' },
    'auth.sign_out': { value: 'Sign out', plural: 'none' },
    'common.save': { value: 'Save', plural: 'none' },
  },
};

function mockSendMessage(routes: Record<string, unknown>) {
  chromeMock.runtime.sendMessage.mockImplementation(
    (message: { type: string }, callback: (response: unknown) => void) => {
      const data = routes[message.type];
      callback(
        data === undefined
          ? { ok: false, error: { code: 'test.missing', message: 'no route' } }
          : { ok: true, data },
      );
    },
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('OptionsApp', () => {
  it('renders the settings sections from stored options', async () => {
    chromeMock.storage.sync.get.mockResolvedValue({
      locale: 'en',
      apiBaseUrl: 'http://localhost:8000/api/v1',
    });
    chromeMock.storage.sync.set.mockResolvedValue(undefined);
    mockSendMessage({
      'get-locales': [
        { code: 'en', fallback_code: null },
        { code: 'pt', fallback_code: 'en' },
      ],
      'get-bundle': bundle,
      'get-account': null,
    });
    render(<OptionsApp />);

    expect(await screen.findByRole('heading', { name: 'Settings' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Language' })).toBeInTheDocument();
    const urlInput = screen.getByLabelText('Base URL') as HTMLInputElement;
    expect(urlInput.value).toBe('http://localhost:8000/api/v1');
  });

  it('saves edited options to chrome.storage.sync', async () => {
    chromeMock.storage.sync.get.mockResolvedValue({
      locale: 'en',
      apiBaseUrl: 'http://localhost:8000/api/v1',
    });
    chromeMock.storage.sync.set.mockResolvedValue(undefined);
    mockSendMessage({
      'get-locales': [{ code: 'en', fallback_code: null }],
      'get-bundle': bundle,
      'get-account': null,
    });
    render(<OptionsApp />);

    const urlInput = (await screen.findByLabelText('Base URL')) as HTMLInputElement;
    fireEvent.change(urlInput, { target: { value: 'https://api.annex.app/api/v1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));

    await waitFor(() => {
      expect(chromeMock.storage.sync.set).toHaveBeenCalledWith(
        expect.objectContaining({ apiBaseUrl: 'https://api.annex.app/api/v1' }),
      );
    });
    expect(await screen.findByText('Save ✓')).toBeInTheDocument();
  });

  it('shows the account section and signs the user out', async () => {
    chromeMock.storage.sync.get.mockResolvedValue({
      locale: 'en',
      apiBaseUrl: 'http://localhost:8000/api/v1',
    });
    chromeMock.storage.sync.set.mockResolvedValue(undefined);
    mockSendMessage({
      'get-locales': [{ code: 'en', fallback_code: null }],
      'get-bundle': bundle,
      'get-account': { uid: 'u1', email: 'reader@example.com', displayName: null },
      'sign-out': null,
    });
    render(<OptionsApp />);

    expect(await screen.findByText('reader@example.com')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await waitFor(() =>
      expect(chromeMock.runtime.sendMessage).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'sign-out' }),
        expect.any(Function),
      ),
    );
  });
});
