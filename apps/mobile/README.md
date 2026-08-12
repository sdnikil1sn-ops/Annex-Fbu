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
  settings (language/theme). 17 unit + widget tests.

## Implemented (Phase 9)

```text
mobile/
├── lib/
│   ├── main.dart             # Composition root: Firebase + API + i18n wiring
│   ├── app/                  # App shell (AnnexApp, AppScope DI, navigation)
│   ├── core/
│   │   ├── config.dart       # API base URL via --dart-define
│   │   └── api/              # AnalysisApi (HTTP) + MockAnalysisApi
│   ├── features/
│   │   ├── auth/             # AuthGateway + Firebase impl + mock + controller
│   │   ├── analysis/         # AnalysisController (submit + poll) + screen
│   │   └── settings/         # Language/theme settings + screen
│   └── l10n/                 # I18nController: runtime bundle loading
├── test/                     # Controller + widget tests (17)
└── pubspec.yaml
```

Run it: `flutter run` (debug builds use the mock API; point at the real
backend with `--dart-define=ANNEX_API_URL=... --dart-define=ANNEX_USE_MOCK=false`).
