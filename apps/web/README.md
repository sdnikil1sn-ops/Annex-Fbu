# `apps/web/` — ANNEX Web App (Flutter Web)

The **Flutter Web** entry point of the same product codebase that powers the mobile
app. Sharing the Dart codebase avoids duplicating business logic between platforms
(DRY) while letting the web build specialize where the platform demands it.

## Layout

```text
web/
├── lib/
│   ├── main.dart             # Composition root (Firebase + API + i18n wiring)
│   ├── app/web_shell.dart    # Responsive shell: rail (wide) / nav bar (narrow)
│   └── core/config.dart      # API base URL via --dart-define
├── web/                      # Web entry: index.html, manifest.json (PWA), icons
├── test/                     # Widget tests for the responsive shell
├── scripts/generate_icons.mjs # PWA icon generation (no binary assets in git)
├── firebase.json             # Firebase Hosting config (public: build/web)
├── .firebaserc               # Hosting project binding
└── pubspec.yaml
```

## Web-specific responsibilities

- **PWA** — service worker and offline-first behavior via Flutter's web support
  (`web/manifest.json`, icons, installable).
- **Firebase Hosting** — deployment configuration (`firebase.json` + `.firebaserc`);
  the release pipeline deploys `build/web` on every `v*` tag
  (`.github/workflows/release.yml` → `deploy-web` job).
- **Responsive layout** — `WebShell` adapts navigation: a rail on wide viewports,
  a bottom navigation bar on narrow ones.
- **Shared features** — everything else comes from `packages/shared_features`
  (Phase 12): auth, analysis, settings, runtime i18n, and the composition root.

## Relationship to `../mobile/`

`web/` and `mobile/` intentionally share feature code through
`packages/shared_features` and `packages/shared_*`. Each app directory keeps only
platform-specific shell, theming, and entry-point code.

## Status

- **Phase 1:** directory documented and reserved.
- **Phase 8:** Flutter Web project scaffold, PWA setup, shared-shell wiring.
- **Phase 11 (documented):** Firebase Hosting deployment steps in
  `docs/guides/deployment.md` §11.
- **Phase 12 (done):** real Flutter Web app — shared features extracted to
  `packages/shared_features`, responsive `WebShell`, PWA manifest + icons,
  Firebase Hosting config (`firebase.json`/`.firebaserc`), widget tests, and the
  `deploy-web` CI job that ships `build/web` on release tags.
- **Phase 16 (done):** lessons curriculum surfaced — the education flow
  (localized lesson list with progress, content detail, idempotent
  completion) ships from `shared_features` as a rail/nav destination.
- **Phase 20 (done):** educator tools surfaced — the classes flow
  (list with role + invite-code pills, create/join dialogs, roster,
  assignments with completion stats, teacher progress/delete actions)
  ships from `shared_features` as a rail/nav destination.
- **Phase 21 (done):** community translations surfaced — the contributor
  flow (untranslated keys for the active locale, propose dialog, own
  submissions with status) ships from `shared_features` as a
  rail/nav destination.
- **Phase 22 (done):** source credibility registry surfaced — search
  publishers/domains, open a profile with the model score and the
  community signal side by side, and rate a source 1–5 (one voice per
  user) as a rail/nav destination.
- **Phase 23 (done):** moderator review queue surfaced — reviewers see
  pending translation suggestions with approve/reject actions inside the
  Contribute destination (role hydrated from `/users/me`).

Run it: `flutter run -d chrome` (debug builds use the mock API; point at the real
backend with `--dart-define=ANNEX_API_URL=... --dart-define=ANNEX_USE_MOCK=false`).
