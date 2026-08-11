# `apps/` — Runable Applications

This directory contains every runnable product surface of ANNEX. Each app is an
independent deployable unit; apps never import from each other, they only consume
the shared packages under [`../packages/`](../packages/README.md).

| Directory | App | Framework | Platforms |
|---|---|---|---|
| [`mobile/`](./mobile/README.md) | ANNEX mobile app | Flutter | Android, iOS, Windows, Linux, macOS |
| [`web/`](./web/README.md) | ANNEX web app | Flutter Web | Web (PWA) |
| [`extension/`](./extension/README.md) | ANNEX browser extension | React + TypeScript | Chrome, Edge, Firefox |

## Rules

- Each app owns its entry point, routing, theming overrides, and platform config.
- Business logic lives in feature modules inside each app; shared logic lives in
  `packages/shared_*` (never duplicated — DRY).
- Apps read configuration from environment/`.env` files at runtime; no secrets are
  compiled into binaries.

## Status

- `mobile/`, `web/`, and `extension/` are scaffolded as documented directories.
  Implementation begins in **Phase 8** (Flutter apps) and **Phase 10** (extension).
