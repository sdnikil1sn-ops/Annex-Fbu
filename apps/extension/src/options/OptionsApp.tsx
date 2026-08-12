import React, { useCallback, useEffect, useState } from 'react';
import { sendMessage } from '../shared/bridge';
import { LocaleInfo, StringKeys, TranslationBundle, translate } from '../shared/i18n';

/** Extension preferences persisted in chrome.storage.sync. */
export interface Options {
  locale: string;
  apiBaseUrl: string;
}

const DEFAULTS: Options = { locale: 'en', apiBaseUrl: 'http://localhost:8000/api/v1' };

export function OptionsApp(): React.JSX.Element {
  const [options, setOptions] = useState<Options>(DEFAULTS);
  const [locales, setLocales] = useState<LocaleInfo[]>([]);
  const [bundle, setBundle] = useState<TranslationBundle | null>(null);
  const [account, setAccount] = useState<{ email: string | null } | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void chrome.storage.sync.get(['locale', 'apiBaseUrl']).then((stored) => {
      const storedOptions: Options = {
        locale: (stored.locale as string | undefined) ?? DEFAULTS.locale,
        apiBaseUrl: (stored.apiBaseUrl as string | undefined) ?? DEFAULTS.apiBaseUrl,
      };
      setOptions(storedOptions);
    });
    void (async () => {
      try {
        const list = await sendMessage<LocaleInfo[]>('get-locales', {});
        setLocales(list);
        const stored = await chrome.storage.sync.get('locale');
        const loaded = await sendMessage<TranslationBundle>('get-bundle', {
          locale: (stored.locale as string | undefined) ?? 'en',
        });
        setBundle(loaded);
      } catch {
        // Locale list is best-effort; the form still works with the defaults.
      }
      try {
        const user = await sendMessage<{ email: string | null } | null>('get-account', {});
        if (user) setAccount(user);
      } catch {
        // Signed out is a valid state.
      }
    })();
  }, []);

  const t = useCallback(
    (key: string) =>
      translate(
        key as Parameters<typeof translate>[0],
        bundle ?? { locale: options.locale, fallback_locale: null, version: 0, entries: {} },
      ),
    [bundle, options.locale],
  );

  const save = useCallback(async () => {
    setSaved(false);
    setError(null);
    try {
      await chrome.storage.sync.set(options);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2_000);
    } catch (e) {
      setError(messageOf(e));
    }
  }, [options]);

  const signOut = useCallback(async () => {
    try {
      await sendMessage('sign-out', {});
      setAccount(null);
    } catch (e) {
      setError(messageOf(e));
    }
  }, []);

  const signIn = useCallback(async () => {
    try {
      const user = await sendMessage<{ email: string | null }>('sign-in', {});
      setAccount(user);
    } catch (e) {
      setError(messageOf(e));
    }
  }, []);

  return (
    <main className="options">
      <h1>{t(StringKeys.settingsTitle)}</h1>
      <section className="options__section">
        <h2>{t(StringKeys.settingsLanguage)}</h2>
        <select
          value={options.locale}
          onChange={(event) => setOptions((prev) => ({ ...prev, locale: event.target.value }))}
        >
          {locales.length === 0 && <option value={options.locale}>{options.locale}</option>}
          {locales.map((locale) => (
            <option key={locale.code} value={locale.code}>
              {locale.code}
            </option>
          ))}
        </select>
      </section>{' '}
      <section className="options__section">
        <h2>{t(StringKeys.settingsApi)}</h2>
        <label className="options__label">
          <span>{t(StringKeys.settingsApiBaseUrl)}</span>
          <input
            type="url"
            value={options.apiBaseUrl}
            onChange={(event) =>
              setOptions((prev) => ({ ...prev, apiBaseUrl: event.target.value }))
            }
          />
        </label>
      </section>
      <section className="options__section">
        <h2>{t(StringKeys.settingsAccount)}</h2>
        {account ? (
          <div className="options__account">
            <span>{account.email ?? t(StringKeys.authSignedIn)}</span>
            <button type="button" onClick={() => void signOut()}>
              {t(StringKeys.authSignOut)}
            </button>
          </div>
        ) : (
          <button type="button" onClick={() => void signIn()}>
            {t(StringKeys.authContinueGoogle)}
          </button>
        )}
      </section>
      {error && (
        <p className="options__error" role="alert">
          {error}
        </p>
      )}
      {saved && (
        <p className="options__saved" role="status">
          {t(StringKeys.commonSave)} ✓
        </p>
      )}
      <button type="button" className="options__save" onClick={() => void save()}>
        {t(StringKeys.commonSave)}
      </button>
    </main>
  );
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
