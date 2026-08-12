# `apps/extension/` — ANNEX Browser Extension

A **React + TypeScript** browser extension (Manifest V3) that brings media-literacy
verification directly into the browsing context — Chrome, Edge, and Firefox.

## Status: Phase 10 complete

The full extension scaffold is implemented: typed Manifest V3, background service
worker, content-script claim highlighting, popup and options React apps, typed
message contracts across all contexts, Firebase Auth, and Vitest coverage.

```text
extension/
├── src/
│   ├── background/           # Service worker: messaging, context menus, API calls
│   ├── content/              # Content script: claim highlighting, selection bridge
│   ├── popup/                # Popup UI: quick verification, score summaries
│   ├── options/              # Options page: language, API URL, account
│   ├── shared/               # Contracts, models, i18n, API client, auth
│   └── manifest.ts           # Manifest V3 (typed, single source of truth)
├── public/icons/             # Generated PNG icons (scripts/generate-icons.mjs)
├── scripts/                  # Icon generation + per-entry IIFE build
├── tests/                    # Vitest unit + component tests (jsdom + chrome mock)
├── popup.html / options.html # HTML entries (emit to dist/ root)
└── package.json
```

## Capabilities

- **Context-menu analysis** — right-click any selection → "Verify with ANNEX";
  the text is handed to the content script for highlighting while the popup
  drives the verification flow.
- **Inline claim highlighting** — the content script wraps matched claim text in
  `<mark class="annex-highlight">` with a per-claim verifiability score.
  Matching is node-based (never `innerHTML`): server content is treated as
  untrusted data, so no markup can execute on the page.
- **Popup verification** — pre-filled from the page selection, submits text,
  polls `GET /analysis/{id}` until terminal, and renders the credibility score
  - per-claim list.
- **Options page** — default language, backend API URL, and account management
  (Google sign-in / sign-out), persisted in `chrome.storage.sync`.
- **Firebase Auth** (ADR-0005) — Google popup sign-in behind an `AuthGateway`
  port with an explicit mock; the ID token flows to the API client as a bearer
  token.
- **Language-aware** — same runtime-i18n architecture as the apps: versioned
  bundles from `GET /i18n/bundles/{locale}` with typed `StringKeys`.

## Architecture

- **Typed message contracts** (`src/shared/contracts.ts`) — every cross-context
  message flows through a `RequestMessage`/`ResponseMessage` envelope; the
  background's `handleRequest` is a strict router, unknown types fail closed.
- **Network isolation** — only the background service worker talks to the
  backend (`HttpApiClient`); content scripts never touch the network.
- **Context menus** register on install; the context-menu click bridges the
  selection to the content script, and the popup is the verification driver.

## Development

```bash
npm install
npm test          # vitest (jsdom, chrome API mocked)
npm run lint      # eslint (flat config)
npm run format    # prettier --write
npm run typecheck # tsc --noEmit
npm run build     # typecheck + icons + popup/options + background/content IIFE
npm run e2e       # end-to-end harness (see below)
```

### End-to-end harness

`npm run e2e` loads the built `dist/` into **Chrome for Testing** via Puppeteer
and drives the full verify-selection flow against a mock v1 backend on
`localhost:8010` — selection bridge, context-menu marking, claim highlighting,
background router + HTTP client (verify → poll → completed report), and the
popup UI (13 checks). Run `npm run build` first; the harness needs the
Puppeteer-managed Chrome (installed automatically with `npm install`, or point
`PUPPETEER_EXECUTABLE_PATH` at any Chrome/Chromium binary).

The mock port defaults to `8010` and must be listed in the built manifest's
`host_permissions` (currently `8000` and `8010`) — the harness fails fast if
`MOCK_PORT` is set to a port the extension cannot reach.

The build emits a loadable unpacked extension in `dist/`:

```text
dist/
├── manifest.json     # generated from src/manifest.ts
├── popup.html        # action.default_popup
├── options.html      # options_page
├── background.js     # background.service_worker (IIFE)
├── content.js        # content_scripts[0].js (IIFE)
├── assets/           # hashed popup/options bundles + CSS
└── icons/            # 16/48/128 PNG icons
```

Load it in Chrome via `chrome://extensions` → Developer mode → "Load unpacked"
→ select `apps/extension/dist`.

## Security notes

- Content scripts communicate via strict message contracts — no `eval`, and
  highlighting never sets `innerHTML` with untrusted data (XSS guard).
- All API calls authenticate through the user's ANNEX session; secrets never
  ship inside the extension bundle.
- Least-privilege permissions: `contextMenus`, `activeTab`, `scripting`,
  `storage` only; host permissions are limited to the ANNEX API.
