# `apps/mobile/` — ANNEX Mobile App (Flutter)

The flagship Flutter application targeting **Android, iOS, Windows, Linux, and
macOS** from a single codebase.

## Planned contents (implemented in Phase 8–9)

```text
mobile/
├── lib/
│   ├── app/                  # App shell: routing, DI composition root, theming
│   ├── core/                 # Cross-cutting infrastructure (network, storage, logging)
│   ├── features/
│   │   ├── auth/             # Sign-in, session, account
│   │   ├── feed/             # Content feed and subscriptions
│   │   ├── analysis/         # Claim/article/image analysis flows
│   │   ├── sources/          # Source credibility scores and history
│   │   ├── education/        # Media literacy lessons and checklists
│   │   └── settings/         # Preferences, language, privacy
│   └── l10n/                 # Runtime-loaded translations (unlimited locales)
├── test/                     # Unit + widget tests per feature
└── pubspec.yaml
```

## Architecture

- **MVVM / Clean Architecture** with feature-first layout (see `CONTRIBUTING.md`).
- Dependency injection via the project's chosen DI framework (decided in Phase 8).
- Data access through repositories; remote data comes from the ANNEX backend API
  and Supabase.
- i18n keys resolved at runtime — adding a language never requires a rebuild.

## Status

- **Phase 1:** directory documented and reserved.
- **Phase 8:** Flutter project scaffold, architecture, theming, i18n foundation.
- **Phase 9 (done):** core feature implementation — app shell with the
  analysis flow (submit text → poll → render the claim report), Firebase
  Auth SDK gateway (anonymous/email/Google) with an explicit mock,
  runtime i18n wired to the backend bundles through `StringKeys`, and
  settings (language/theme).
- **Phase 12 (done):** feature code extracted to
  `packages/shared_features` and shared with the web app; the app now
  contributes only its platform-specific shell and entry point.
- **Phase 16 (done):** lessons curriculum surfaced — the education flow
  (localized lesson list with progress, content detail, idempotent
  completion) ships from `shared_features` as a third bottom tab.
- **Phase 20 (done):** educator tools surfaced — the classes flow
  (list with role + invite-code pills, create/join dialogs, roster,
  assignments with completion stats, teacher progress/delete actions)
  ships from `shared_features` as a fourth bottom tab.

## Implemented (Phase 9 → 12)

```text
mobile/
├── lib/
│   ├── main.dart             # Composition root: Firebase + API + i18n wiring
│   ├── app/annex_app.dart    # Mobile shell: MaterialApp + bottom tabs
│   └── core/config.dart      # API base URL via --dart-define
├── test/                     # Widget tests (4): sign-in gate, full flow, lessons
└── pubspec.yaml
```

All feature code — the API client, auth gateway (Firebase impl + mock),
runtime i18n, the analysis and settings flows, and the `AppScope`
composition root — lives in `packages/shared_features` (Phase 12) and is
shared with `apps/web`.

Run it: `flutter run` (debug builds use the mock API; point at the real
backend with `--dart-define=ANNEX_API_URL=... --dart-define=ANNEX_USE_MOCK=false`).
