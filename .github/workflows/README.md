# CI/CD Workflows

This directory hosts the GitHub Actions workflows that power ANNEX's continuous
integration and delivery pipeline.

## Current status

The repository is in **Phase 1 (Foundation)** — no application code exists yet,
so no workflows are defined. Workflows are introduced as their targets exist:

| Planned workflow | Introduced in | Purpose |
|---|---|---|
| `ci.yml` | Phase 2 | Lint, format, and unit-test the Python backend on every push/PR |
| `flutter.yml` | Phase 8 | `dart format --set-exit-if-changed`, `dart analyze`, `flutter test` for apps/packages |
| `extension.yml` | Phase 10 | ESLint, Prettier, and vitest for the browser extension |
| `docker.yml` | Phase 7 | Build and scan container images |
| `release.yml` | Phase 11 | Versioned builds, Firebase Hosting deploy, Cloud Run deploy |
| `security.yml` | Phase 11 | Dependency vulnerability scanning + SAST |

## Policy

- Every workflow must run on `pull_request` to `main` (and `push` to `main` where
  appropriate).
- Secrets are injected via GitHub Environments / repository secrets — never
  hardcoded in workflow files.
- All workflows must complete successfully before a release is cut.
