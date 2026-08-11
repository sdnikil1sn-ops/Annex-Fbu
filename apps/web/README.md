# `apps/web/` — ANNEX Web App (Flutter Web)

The **Flutter Web** entry point of the same product codebase that powers the mobile
app. Sharing the Dart codebase avoids duplicating business logic between platforms
(DRY) while letting the web build specialize where the platform demands it.

## Planned contents (implemented in Phase 8–9)

```text
web/
├── web/                      # Web entry point, manifest.json, index.html
├── lib/
│   └── app/                  # Web-specific app shell wiring (shared features reused)
├── test/                     # Widget tests for web behavior
└── pubspec.yaml
```

## Web-specific responsibilities

- **PWA** — service worker and offline-first behavior via Flutter's web support.
- **Firebase Hosting** — deployment configuration (landing in Phase 11).
- **Responsive layout** — adaptive navigation for desktop and mobile browsers.
- **Deep linking** — web route structure mapped to the shared app router.

## Relationship to `../mobile/`

`web/` and `mobile/` intentionally share feature code through `packages/shared_*`
and a shared feature library. Each app directory keeps only platform-specific
shell, theming, and entry-point code.

## Status

- **Phase 1:** directory documented and reserved.
- **Phase 8:** Flutter Web project scaffold, PWA setup, shared-shell wiring.
- **Phase 11:** Firebase Hosting deployment pipeline.
