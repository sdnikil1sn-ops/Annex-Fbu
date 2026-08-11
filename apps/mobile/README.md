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
- **Phase 9:** core feature implementation.
