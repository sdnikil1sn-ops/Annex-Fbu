import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Analysis, AnalysisReport, credibilityScore, isTerminal } from '../shared/analysis';
import { sendMessage } from '../shared/bridge';
import { StringKeys, TranslationBundle, translate } from '../shared/i18n';

/** Poll interval for pending/processing analyses (ms). */
const POLL_INTERVAL_MS = 2_000;
/** Give up after this many polls and surface a manual retry. */
const MAX_POLLS = 15;

type FlowState =
  | { phase: 'idle' }
  | { phase: 'loading-bundle' }
  | { phase: 'submitting' }
  | { phase: 'polling'; analysisId: string }
  | { phase: 'done'; analysis: Analysis }
  | { phase: 'error'; message: string };

/** Ask the active tab's content script for the current selection. */
async function getSelection(): Promise<string> {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const tab = tabs[0];
  if (!tab?.id) return '';
  try {
    const response = await chrome.tabs.sendMessage(tab.id, {
      type: 'annex:get-selection',
    });
    return typeof response?.text === 'string' ? response.text : '';
  } catch {
    return ''; // no content script on this page (e.g. chrome:// pages)
  }
}

export function PopupApp(): React.JSX.Element {
  const [state, setState] = useState<FlowState>({ phase: 'idle' });
  const [text, setText] = useState('');
  const [bundle, setBundle] = useState<TranslationBundle | null>(null);
  const [locale, setLocale] = useState('en');
  const [account, setAccount] = useState<{ email: string | null } | null>(null);
  const pollRef = useRef<number | null>(null);
  // Hoisted so the polling effect's dependency array stays type-safe.
  const pollingId = state.phase === 'polling' ? state.analysisId : null;

  const t = useCallback(
    (key: string) =>
      translate(key as Parameters<typeof translate>[0], bundle ?? emptyBundle(locale)),
    [bundle, locale],
  );

  // Load the locale list, the active bundle, and the account on mount.
  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        const locales = await sendMessage<{ code: string }[]>('get-locales', {});
        const code = locales.find((l) => l.code === 'en')?.code ?? locales[0]?.code ?? 'en';
        if (!cancelled) setLocale(code);
        const loaded = await sendMessage<TranslationBundle>('get-bundle', { locale: code });
        if (!cancelled) setBundle(loaded);
      } catch {
        // Fall back to the key-based bundle; the UI still renders.
      }
      try {
        const user = await sendMessage<{ email: string | null } | null>('get-account', {});
        if (!cancelled && user) setAccount(user);
      } catch {
        // Signed-out state is fine.
      }
      const selection = await getSelection();
      if (!cancelled && selection) setText(selection);
    }
    void init();
    return () => {
      cancelled = true;
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
    };
  }, []);

  // Poll until terminal while in the polling phase.
  useEffect(() => {
    if (pollingId === null) return;
    const analysisId = pollingId;
    let polls = 0;
    pollRef.current = window.setInterval(() => {
      void (async () => {
        polls += 1;
        try {
          const analysis = await sendMessage<Analysis>('fetch-analysis', {
            id: analysisId,
          });
          if (isTerminal(analysis.status)) {
            if (pollRef.current !== null) window.clearInterval(pollRef.current);
            setState({ phase: 'done', analysis });
          } else if (polls >= MAX_POLLS) {
            if (pollRef.current !== null) window.clearInterval(pollRef.current);
            setState({ phase: 'error', message: t(StringKeys.commonRetry) });
          }
        } catch (error) {
          if (pollRef.current !== null) window.clearInterval(pollRef.current);
          setState({ phase: 'error', message: messageOf(error) });
        }
      })();
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current !== null) window.clearInterval(pollRef.current);
    };
  }, [pollingId, t]);

  const submit = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || state.phase === 'submitting') return;
    setState({ phase: 'submitting' });
    try {
      const analysis = await sendMessage<Analysis>('verify', { text: trimmed, locale });
      if (isTerminal(analysis.status)) {
        setState({ phase: 'done', analysis });
      } else {
        setState({ phase: 'polling', analysisId: analysis.id });
      }
    } catch (error) {
      setState({ phase: 'error', message: messageOf(error) });
    }
  }, [text, locale, state.phase]);

  const signIn = useCallback(async () => {
    try {
      const user = await sendMessage<{ email: string | null }>('sign-in', {});
      setAccount(user);
    } catch (error) {
      setState({ phase: 'error', message: messageOf(error) });
    }
  }, []);

  const retry = useCallback(() => {
    setState({ phase: 'idle' });
    void submit();
  }, [submit]);

  // When the report lands, forward its claims to the content script so the
  // claims get highlighted inline on the page (Phase 10 highlight engine).
  useEffect(() => {
    if (state.phase !== 'done') return;
    const claims = state.analysis.report?.claims;
    if (!claims || claims.length === 0) return;
    void (async () => {
      try {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        const tab = tabs[0];
        if (!tab?.id) return;
        await chrome.tabs.sendMessage(tab.id, {
          type: 'highlight-claims',
          requestId: 'popup-highlight',
          payload: {
            claims: claims.map((claim) => ({
              text: claim.text,
              verifiability: claim.verifiability,
            })),
          },
        });
      } catch {
        // Highlighting is best-effort; the report still renders in the popup.
      }
    })();
  }, [state]);

  const busy =
    state.phase === 'submitting' || state.phase === 'polling' || state.phase === 'loading-bundle';

  return (
    <div className="popup">
      <header className="popup__header">
        <span className="popup__logo">ANNEX</span>
        {account ? (
          <span className="popup__account">{account.email}</span>
        ) : (
          <button type="button" className="popup__link" onClick={() => void signIn()}>
            {t(StringKeys.authContinueGoogle)}
          </button>
        )}
      </header>

      <main className="popup__body">
        {state.phase === 'done' ? (
          <ReportView analysis={state.analysis} t={t} onNew={() => setState({ phase: 'idle' })} />
        ) : state.phase === 'error' ? (
          <div className="popup__error" role="alert">
            <p>{state.message}</p>
            <button type="button" className="popup__button" onClick={retry}>
              {t(StringKeys.commonRetry)}
            </button>
          </div>
        ) : (
          <>
            <textarea
              className="popup__input"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={t(StringKeys.analysisInputHint)}
              rows={4}
              disabled={busy}
            />
            <button
              type="button"
              className="popup__button popup__button--primary"
              onClick={() => void submit()}
              disabled={busy || !text.trim()}
            >
              {busy ? t(StringKeys.commonLoading) : t(StringKeys.analysisSubmit)}
            </button>
          </>
        )}
      </main>
    </div>
  );
}

/** Terminal-state report: overall score + per-claim list. */
function ReportView({
  analysis,
  t,
  onNew,
}: {
  analysis: Analysis;
  t: (key: string) => string;
  onNew: () => void;
}): React.JSX.Element {
  const report = analysis.report as AnalysisReport | null;
  const score = report ? credibilityScore(report) : 0;

  return (
    <section className="report">
      {analysis.status === 'failed' ? (
        <p className="report__failed" role="alert">
          {t(StringKeys.analysisFailed)}: {analysis.failure_reason ?? ''}
        </p>
      ) : (
        <>
          <div className="report__score">
            <span className="report__score-value">{Math.round(score * 100)}%</span>
            <span className="report__score-label">{t(StringKeys.analysisCredibilityScore)}</span>
          </div>
          <p className="report__summary">{report?.summary ?? ''}</p>
          <ul className="report__claims">
            {(report?.claims ?? []).map((claim, index) => (
              <li key={`${index}-${claim.text.slice(0, 24)}`} className="report__claim">
                <span
                  className="report__claim-dot"
                  style={{ background: scoreColor(claim.verifiability) }}
                />
                <span className="report__claim-text">{claim.text}</span>
                <span className="report__claim-score">
                  {Math.round(claim.verifiability * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      <button type="button" className="popup__button" onClick={onNew}>
        {t(StringKeys.analysisSubmit)}
      </button>
    </section>
  );
}

/** Verifiability → color (red → amber → green). */
function scoreColor(verifiability: number): string {
  const hue = Math.max(0, Math.min(120, verifiability * 120));
  return `hsl(${hue} 70% 45%)`;
}

function emptyBundle(locale: string): TranslationBundle {
  return { locale, fallback_locale: null, version: 0, entries: {} };
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
