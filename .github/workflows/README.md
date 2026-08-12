# CI/CD Workflows

This directory hosts the GitHub Actions workflows that power ANNEX's continuous
integration and delivery pipeline.

## Current workflows

| Workflow | Introduced in | Purpose |
|---|---|---|
| `ci.yml` | Phase 2 | Repository validation: YAML syntax, markdown links, required files, secret patterns |
| `backend.yml` | Phase 3 | Ruff, mypy, pytest with coverage for the FastAPI service |
| `docker.yml` | Phase 7 | Build and scan container images |
| `dart.yml` | Phase 8 | Format, analyze, test for pure-Dart packages (`shared_utils`) |
| `flutter.yml` | Phase 9 | Format, analyze, test for Flutter app + packages |

## Planned additions

| Workflow | Introduced in | Purpose |
|---|---|---|
| `extension.yml` | Phase 10 | ESLint, Prettier, vitest for the browser extension |
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
