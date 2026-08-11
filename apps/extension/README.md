# `apps/extension/` — ANNEX Browser Extension

A **React + TypeScript** browser extension (Manifest V3) that brings media-literacy
verification directly into the browsing context — Chrome, Edge, and Firefox.

## Planned contents (implemented in Phase 10)

```text
extension/
├── src/
│   ├── background/           # Service worker: messaging, context menus, API calls
│   ├── content/              # Content scripts: claim highlighting, page inspection
│   ├── popup/                # Popup UI: quick verification, score summaries
│   ├── options/              # Options page: language, privacy, account
│   ├── shared/               # Types and utilities shared across contexts
│   └── manifest.ts           # Manifest V3 (typed, generated)
├── public/                   # Static icons and assets
├── tests/                    # Vitest unit + integration tests
└── package.json
```

## Planned capabilities

- **Context-menu analysis** — verify selected text or image URLs instantly.
- **Inline claim highlighting** — annotate pages with credibility signals.
- **Source scoring** — domain/publisher trust scores on hover.
- **Screenshot + OCR pipeline** — send page captures to the backend for analysis.
- **Language-aware** — same runtime-i18n architecture as the apps.

## Security notes

- Content scripts communicate with the background service worker via strict
  message contracts — no `eval`, no `innerHTML` with untrusted data (XSS guard).
- All API calls authenticate through the user's ANNEX session; secrets never ship
  inside the extension bundle.

## Status

- **Phase 1:** directory documented and reserved.
- **Phase 10:** extension scaffold, manifest, popup/content/background modules.
