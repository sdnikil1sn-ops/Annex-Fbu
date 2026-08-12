/**
 * End-to-end test for the built extension (Phase 10).
 *
 * Loads the real `dist/` bundle into Chrome for Testing (via Puppeteer —
 * the installed system Chrome blocks `--load-extension` on this machine)
 * and drives the verify-selection flow end to end:
 *
 *   1. content-script selection bridge (`annex:get-selection`)
 *   2. context-menu marking (`annex:selection` → <mark class="annex-selection">)
 *   3. claim highlighting (`highlight-claims` → <mark class="annex-highlight">)
 *   4. background router + HTTP API client (`verify` → `fetch-analysis`)
 *      against a mock v1 backend
 *   5. the popup UI: type text → Analyze → poll → rendered report
 *
 * The harness uses two launches sharing one profile: the first seeds the
 * stored API URL (the options-page setting), the second runs the checks so
 * the worker reads it through its real startup composition root. This
 * avoids chrome.runtime.reload(), after which Chrome reuses the worker
 * target and CDP re-attachment is unreliable.
 *
 * Usage: node scripts/e2e.mjs   (from apps/extension; puppeteer is a dev dep)
 * Env:   PUPPETEER_EXECUTABLE_PATH  chrome to test with (defaults to the
 *        Puppeteer-managed Chrome for Testing build)
 *        MOCK_PORT / DIST_DIR        harness overrides
 */
import puppeteer from 'puppeteer';
import http from 'node:http';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const DIST = process.env.DIST_DIR || join(ROOT, 'dist');
// Port 8000 may be taken by unrelated software; the harness owns 8010 and
// points the extension at it via chrome.storage.sync (the options setting).
// The chosen port MUST be listed in the built manifest's host_permissions
// (see the check below) or the background's fetch will fail silently.
const MOCK_PORT = Number(process.env.MOCK_PORT || 8010);
const API_BASE_URL = `http://localhost:${MOCK_PORT}/api/v1`;

/* ------------------------------------------------------------------ */
/* Mock v1 backend (analysis + i18n endpoints)                         */
/* ------------------------------------------------------------------ */

const CLAIMS = [
  { text: 'The Earth orbits the Sun once per year', verifiability: 0.9 },
  { text: 'cats have nine lives', verifiability: 0.15 },
];

const REPORT = {
  summary: 'The first claim is verifiable; the second is a myth.',
  claims: CLAIMS,
};

const BUNDLE_EN = {
  locale: 'en',
  fallback_locale: null,
  version: 1,
  entries: {
    'analysis.submit': { value: 'Analyze', plural: 'none' },
    'analysis.input_hint': { value: 'Paste or select text…', plural: 'none' },
    'analysis.credibility_score': { value: 'Credibility score', plural: 'none' },
    'common.retry': { value: 'Retry', plural: 'none' },
    'common.loading': { value: 'Loading…', plural: 'none' },
    'common.learn_before_you_believe': { value: 'Learn before you believe.', plural: 'none' },
    'auth.continue_google': { value: 'Sign in with Google', plural: 'none' },
  },
};

const PAGE_HTML = `<!doctype html><html><head><meta charset="utf-8"><title>Annex E2E</title></head>
<body><article><h1>Science Roundup</h1>
<p>Scientists agree that the Earth orbits the Sun once per year and that ocean tides follow the Moon.</p>
<p>Some people claim that cats have nine lives, but there is no evidence for this at all.</p>
</article></body></html>`;

/* global chrome, document, getSelection, HTMLTextAreaElement */

const analyses = new Map();
let nextId = 1;

function json(res, status, body) {
  const data = JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(data),
    'access-control-allow-origin': '*',
    'access-control-allow-headers': 'authorization, content-type',
  });
  res.end(data);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${MOCK_PORT}`);
  const path = url.pathname;

  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'access-control-allow-origin': '*',
      'access-control-allow-methods': 'GET,POST,OPTIONS',
    });
    res.end();
    return;
  }

  if (req.method === 'GET' && path === '/page.html') {
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(PAGE_HTML);
    return;
  }

  if (req.method === 'GET' && path === '/api/v1/i18n/locales') {
    json(res, 200, {
      data: {
        locales: [
          { code: 'en', fallback_code: null },
          { code: 'pt', fallback_code: 'en' },
        ],
      },
    });
    return;
  }

  const bundleMatch = path.match(/^\/api\/v1\/i18n\/bundles\/([^/]+)$/);
  if (req.method === 'GET' && bundleMatch) {
    json(res, 200, { data: BUNDLE_EN });
    return;
  }

  if (req.method === 'POST' && path === '/api/v1/analysis') {
    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', () => {
      let payload = {};
      try {
        payload = JSON.parse(body || '{}');
      } catch {
        /* default */
      }
      const id = `e2e-${nextId++}`;
      const analysis = {
        id,
        input_type: 'text',
        status: 'pending',
        locale: payload.locale || 'en',
        failure_reason: null,
        report: null,
        created_at: new Date().toISOString(),
        completed_at: null,
        _fetches: 0,
      };
      analyses.set(id, analysis);
      const publicView = { ...analysis };
      delete publicView._fetches;
      json(res, 202, { data: publicView });
    });
    return;
  }

  const analysisMatch = path.match(/^\/api\/v1\/analysis\/([^/]+)$/);
  if (req.method === 'GET' && analysisMatch) {
    const analysis = analyses.get(analysisMatch[1]);
    if (!analysis) {
      json(res, 404, { error: { code: 'analysis.not_found', message: 'not found' } });
      return;
    }
    analysis._fetches += 1;
    // Complete on the second poll to exercise the polling loop.
    if (analysis._fetches >= 2) {
      analysis.status = 'completed';
      analysis.report = REPORT;
      analysis.completed_at = new Date().toISOString();
    }
    const publicView = { ...analysis };
    delete publicView._fetches;
    json(res, 200, { data: publicView });
    return;
  }

  json(res, 404, { error: { code: 'not_found', message: `no route: ${path}` } });
});

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const sleep = (ms) => new Promise((resolvePromise) => setTimeout(resolvePromise, ms));

async function waitFor(fn, timeoutMs, label) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const value = await fn();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await sleep(300);
  }
  throw new Error(`Timed out waiting for ${label}${lastError ? ` (${lastError.message})` : ''}`);
}

const results = [];
function check(name, ok, detail = '') {
  results.push({ name, ok, detail });
  console.log(`${ok ? '  PASS' : '  FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

const step = (label) => console.log(`--- step: ${label}`);

// Hard guard: never run longer than 120s. Track the browser so the guard
// can close it instead of orphaning Chrome (notably on Windows).
let activeBrowser = null;
setTimeout(() => {
  console.error('HARNESS GUARD TIMEOUT — aborting');
  void activeBrowser?.close();
  server.close();
  process.exit(3);
}, 120_000);

async function main() {
  console.log('Starting mock v1 backend on :' + MOCK_PORT);
  await new Promise((resolvePromise) => server.listen(MOCK_PORT, resolvePromise));

  const profileDir = mkdtempSync(join(tmpdir(), 'annex-e2e-'));
  console.log(`Launching Chrome with the extension from ${DIST}`);

  // The built manifest must permit the mock port, or the background's
  // fetch to it will be blocked and every check fails mysteriously.
  const manifest = JSON.parse(readFileSync(join(DIST, 'manifest.json'), 'utf8'));
  const permitsMockPort = (manifest.host_permissions ?? []).some((pattern) =>
    pattern.includes(`localhost:${MOCK_PORT}`),
  );
  if (!permitsMockPort) {
    throw new Error(
      `dist/manifest.json does not grant host permission for localhost:${MOCK_PORT} ` +
        `(host_permissions: ${JSON.stringify(manifest.host_permissions)}). ` +
        'Use a port listed there (8000 or 8010), rebuild dist, or set MOCK_PORT accordingly.',
    );
  }

  const launch = () =>
    puppeteer.launch({
      headless: false,
      userDataDir: profileDir,
      args: [
        `--disable-extensions-except=${DIST}`,
        `--load-extension=${DIST}`,
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-popup-blocking',
      ],
    });
  const waitForWorker = (browser) =>
    browser.waitForTarget(
      (t) => t.type() === 'service_worker' && String(t.url()).includes('background.js'),
      { timeout: 30_000 },
    );

  let browser;
  try {
    step('launch 1: seed stored API URL');
    // --- Launch 1: seed the stored API URL (the options-page setting) ---
    // chrome.storage.sync persists in the profile, so a second launch's
    // worker reads it at startup — exercising the real composition root
    // without a reload (Chrome reuses the worker target across reloads,
    // which makes CDP re-attachment unreliable).
    const seedBrowser = await launch();
    activeBrowser = seedBrowser;
    try {
      const seedWorker = await (await waitForWorker(seedBrowser)).worker();
      const name = await seedWorker.evaluate(() => chrome.runtime.getManifest().name);
      await seedWorker.evaluate(async (baseUrl) => {
        await chrome.storage.sync.set({ apiBaseUrl: baseUrl });
      }, API_BASE_URL);
      console.log(`Seeded ${API_BASE_URL} into the profile (extension: "${name}")`);
    } finally {
      await seedBrowser.close();
      activeBrowser = null;
      // Chrome may still hold the profile/singleton lock right after exit;
      // give it a moment before relaunching (notably on Windows).
      await sleep(1500);
    }

    step('launch 2: real run');
    browser = await launch();
    activeBrowser = browser;
    const workerTarget = await waitForWorker(browser);
    const extensionId = new URL(workerTarget.url()).host;
    const worker = await workerTarget.worker();

    const manifestName = await worker.evaluate(() => chrome.runtime.getManifest().name);
    check(
      'extension service worker registered',
      manifestName.includes('ANNEX'),
      `id=${extensionId} · "${manifestName}"`,
    );

    // The worker's startup composition root must have picked up the stored
    // URL — later checks prove it end to end (verify hits OUR mock).
    const stored = await worker.evaluate(() => chrome.storage.sync.get('apiBaseUrl'));
    check(
      'background reads the stored API URL at startup',
      stored.apiBaseUrl === API_BASE_URL,
      stored.apiBaseUrl,
    );

    step('open test page');
    // --- Test page: navigate a fresh tab, wait for the content script ---
    const page = await browser.newPage();
    const pageErrors = [];
    page.on('pageerror', (error) => pageErrors.push(String(error)));
    await page.goto(`http://localhost:${MOCK_PORT}/page.html`, { waitUntil: 'load' });

    step('open popup');
    // --- Popup page: open it the way the extension does (tabs.create from
    // the worker) — a plain tab navigation to chrome-extension:// URLs is
    // blocked by Chrome's navigation policy, so puppeteer's page.goto can't
    // reach it.
    await worker.evaluate(() => chrome.tabs.create({ url: chrome.runtime.getURL('popup.html') }));
    const popup = await waitFor(
      async () => {
        const pages = await browser.pages();
        const found = pages.find((p) => String(p.url()).includes('popup.html'));
        return found ?? null;
      },
      15_000,
      'popup page target',
    );
    const popupErrors = [];
    popup.on('pageerror', (error) => popupErrors.push(String(error)));
    check(
      'popup page opens as an extension tab',
      String(popup.url()).startsWith(`chrome-extension://${extensionId}/`),
      popup.url(),
    );

    const tabId = await waitFor(
      async () => {
        const tabs = await worker.evaluate(() =>
          chrome.tabs.query({}).then((list) => list.map((t) => ({ id: t.id, url: t.url }))),
        );
        const tab = tabs.find((t) => String(t.url).includes('page.html'));
        if (!tab) return null;
        try {
          await worker.evaluate(
            async (id) => chrome.tabs.sendMessage(id, { type: 'annex:get-selection' }),
            tab.id,
          );
          return tab.id;
        } catch {
          return null;
        }
      },
      15_000,
      'content script injection',
    );
    check('content script injected into test page', Boolean(tabId));

    step('selection bridge');
    // --- 1. Selection bridge ---
    await page.evaluate(() => {
      const range = document.createRange();
      range.selectNodeContents(document.querySelector('p'));
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      return sel.toString();
    });
    const selectedText = await worker.evaluate(
      async (id) => chrome.tabs.sendMessage(id, { type: 'annex:get-selection' }),
      tabId,
    );
    const pageText = await page.evaluate(() => document.querySelector('p').textContent);
    const selectedViaBridge = selectedText?.data?.text;
    check(
      'selection bridge returns the selected text',
      typeof selectedViaBridge === 'string' &&
        selectedViaBridge.length > 0 &&
        selectedViaBridge === pageText,
      JSON.stringify(selectedViaBridge),
    );

    step('context-menu marking');
    // --- 2. Context-menu marking (the exact message the menu fires) ---
    await worker.evaluate(
      async (id, text) => chrome.tabs.sendMessage(id, { type: 'annex:selection', text }),
      tabId,
      pageText,
    );
    const marked = await page.evaluate(
      () => document.querySelectorAll('mark.annex-selection').length,
    );
    check('annex:selection marks the selection on the page', marked > 0, `${marked} mark(s)`);

    step('claim highlighting');
    // --- 3. Claim highlighting ---
    await worker.evaluate(
      async (id, claims) =>
        chrome.tabs.sendMessage(id, {
          type: 'highlight-claims',
          requestId: 'e2e',
          payload: { claims },
        }),
      tabId,
      CLAIMS,
    );
    const highlightMarks = await page.evaluate(() =>
      Array.from(document.querySelectorAll('mark.annex-highlight')).map((m) => ({
        text: m.textContent,
        score: m.getAttribute('data-annex-score'),
      })),
    );
    check(
      'highlight-claims wraps matching claims',
      highlightMarks.length === 2 && highlightMarks.every((m) => m.score),
      highlightMarks.map((m) => `"${m.text.slice(0, 30)}…" (${m.score})`).join(' | '),
    );

    step('popup router checks');
    // --- 4. Popup render + router + HTTP API client ---
    await waitFor(
      async () => (await popup.evaluate(() => !!document.querySelector('textarea'))) === true,
      15_000,
      'popup render',
    );
    check('popup renders the verify form', true, 'textarea visible');

    // Router + HTTP API client: verify → pending, then poll → completed report.
    const verifyResponse = await popup
      .evaluate(
        (payload) =>
          chrome.runtime.sendMessage({ type: 'verify', requestId: 'e2e-verify', payload }),
        { text: 'The Earth orbits the Sun once per year', locale: 'en' },
      )
      .catch((error) => ({ ok: false, error: String(error) }));
    check(
      'verify message hits the mock backend (202 + pending)',
      verifyResponse?.ok === true && verifyResponse?.data?.status === 'pending',
      verifyResponse?.data?.id,
    );

    await sleep(600); // let the mock complete on the next fetch
    const analysisId = verifyResponse?.data?.id;
    const poll1 = await popup
      .evaluate(
        (id) =>
          chrome.runtime.sendMessage({
            type: 'fetch-analysis',
            requestId: 'e2e-poll1',
            payload: { id },
          }),
        analysisId,
      )
      .catch((error) => ({ data: null, error: String(error) }));
    const poll2 = await popup
      .evaluate(
        (id) =>
          chrome.runtime.sendMessage({
            type: 'fetch-analysis',
            requestId: 'e2e-poll2',
            payload: { id },
          }),
        analysisId,
      )
      .catch((error) => ({ data: null, error: String(error) }));
    check(
      'fetch-analysis transitions to completed with the report',
      poll1?.data?.status === 'pending' &&
        poll2?.data?.status === 'completed' &&
        poll2?.data?.report?.claims?.length === 2,
      `${poll1?.data?.status} → ${poll2?.data?.status}`,
    );

    step('popup UI flow');
    // --- 5. Popup UI flow: type text → Analyze → poll → rendered report ---
    await popup.evaluate(() => {
      const ta = document.querySelector('textarea');
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(ta, 'The Earth orbits the Sun once per year');
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      return ta.value;
    });
    await popup.evaluate(() => document.querySelector('button.popup__button--primary').click());

    const report = await waitFor(
      async () => {
        const state = await popup.evaluate(() => ({
          score: document.querySelector('.report__score-value')?.textContent ?? null,
          claims: document.querySelectorAll('.report__claim').length,
          summary: document.querySelector('.report__summary')?.textContent ?? null,
        }));
        return state.score ? state : null;
      },
      20_000,
      'popup report (poll interval 2s)',
    );
    check(
      'popup submits, polls, and renders the report',
      report.score !== null && report.claims === 2,
      `${report.score} · ${report.claims} claims · "${report.summary?.slice(0, 40)}…"`,
    );

    check(
      'no uncaught exceptions in the popup',
      popupErrors.length === 0,
      `${popupErrors.length} exception(s)`,
    );
    check(
      'no uncaught exceptions on the test page',
      pageErrors.length === 0,
      `${pageErrors.length} exception(s)`,
    );
  } finally {
    if (browser) await browser.close();
    activeBrowser = null;
    server.close();
    try {
      await sleep(1000);
      rmSync(profileDir, { recursive: true, force: true });
    } catch {
      /* best-effort cleanup on Windows */
    }
  }

  const failed = results.filter((r) => !r.ok);
  console.log('\n==============================================');
  console.log(
    `E2E ${failed.length === 0 ? 'PASSED' : 'FAILED'} (${results.length - failed.length}/${results.length} checks)`,
  );
  console.log('==============================================');
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error('\nE2E harness error:', error);
  server.close();
  process.exit(1);
});
