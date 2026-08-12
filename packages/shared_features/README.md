# `packages/shared_features/` — Shared Flutter Features

The cross-platform feature layer of the ANNEX Flutter clients (Phase 12).
Everything both apps do the same way lives here — the API client, runtime
i18n, authentication, the analysis flow, and settings — so `apps/mobile`
and `apps/web` keep only their platform-specific shell, theming, and
entry-point code.

## What lives here

| Area | Files |
|---|---|
| API client | `src/api/analysis_api.dart` (HTTP) + `mock_analysis_api.dart` |
| i18n (ADR-0007) | `src/i18n/i18n_controller.dart` |
| Auth (ADR-0005) | `src/features/auth/` — gateway + Firebase impl + mock + controller |
| Analysis flow | `src/features/analysis/` — controller (submit → poll → report) + screen |
| Settings | `src/features/settings/` — language/theme/account + screen |
| Composition root | `src/app/app_scope.dart` — `AppServices` + `AppScope` (ADR-0003) |
| Tests | Controller unit tests + screens exercised via app widget tests |

## Rules

- **No app imports** — this package never imports from `apps/*`.
- **UI via `shared_ui`** — screens use design tokens and components from
  `shared_ui`; raw values never appear in widgets.
- **Contracts via `shared_models`** — domain shapes come from the canonical
  models, serialized compatibly with the backend OpenAPI contract.
- **Mocks are explicit** — test/local-dev fakes are named `Mock*` and are
  never selected in production code paths.

Consumers: `apps/mobile`, `apps/web` (see `packages/README.md`).
