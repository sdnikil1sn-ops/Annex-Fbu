# `packages/` — Internal Shared Packages

Internal libraries shared across the ANNEX apps. Managed as a **Melos** Dart
workspace with path dependencies, so a change in one package propagates instantly
without a registry publish.

## Packages

| Package | Purpose | Consumers |
|---|---|---|
| [`shared_ui/`](./shared_ui/README.md) | Flutter design system: tokens, components, accessibility | `apps/mobile`, `apps/web`, `shared_features` |
| [`shared_features/`](./shared_features/README.md) | Shared Flutter features: API client, auth, i18n, analysis/settings flows, `AppScope` | `apps/mobile`, `apps/web` |
| [`shared_models/`](./shared_models/README.md) | Domain models, JSON Schema contracts, serialization | All apps, mirrored by `backend/` |
| [`shared_utils/`](./shared_utils/README.md) | Pure-Dart utilities: validation, formatting, i18n helpers | All apps and packages |

## Rules

- **No app-specific logic** — a package must never import from an app.
- **No secrets** — packages must run with zero configuration.
- **Backwards compatibility** — internal APIs follow semantic versioning; breaking
  changes are coordinated via Melos versioning across the workspace.
- **Contracts first** — `shared_models` is the single source of truth for domain
  contracts; the backend's Pydantic models are derived from the same OpenAPI spec.

## Status

- **Phase 1:** packages documented and reserved.
- **Phase 8:** Melos workspace bootstrapped; packages scaffolded with `shared_ui`,
  `shared_models`, and `shared_utils` first versions.
- **Phase 12:** `shared_features` added — the cross-platform Flutter feature layer
  (API client, auth gateway, i18n, analysis/settings flows, `AppScope`), consumed
  by `apps/mobile` and `apps/web`.
