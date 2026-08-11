# CI/CD Workflows

This directory hosts the GitHub Actions workflows that power ANNEX's continuous
integration and delivery pipeline.

## Current workflows

| Workflow | Introduced in | Purpose |
|---|---|---|
| `ci.yml` | Phase 2 | Repository validation: YAML syntax, markdown links, required files, secret patterns |

## Planned additions

| Workflow | Introduced in | Purpose |
|---|---|---|
| `backend.yml` | Phase 3 | Ruff, mypy, pytest for the FastAPI service |
| `docker.yml` | Phase 7 | Build and scan container images |
| `flutter.yml` | Phase 8 | `dart format --set-exit-if-changed`, `dart analyze`, `flutter test` |
| `extension.yml` | Phase 10 | ESLint, Prettier, vitest for the browser extension |
| `release.yml` | Phase 11 | Versioned builds, Firebase Hosting deploy, Cloud Run deploy |
| `security.yml` | Phase 11 | Dependency vulnerability scanning + SAST |

## Policy

- Every workflow runs on `pull_request` to `main` (and `push` to `main` where
  appropriate).
- Secrets are injected via GitHub Environments / repository secrets — never
  hardcoded in workflow files.
- Workflows call the scripts under `scripts/` rather than duplicating logic (DRY).
- All workflows must complete successfully before a release is cut.
