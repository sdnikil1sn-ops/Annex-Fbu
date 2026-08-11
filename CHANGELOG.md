# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Repository foundation (Phase 1).**
  - `LICENSE` — Apache License 2.0.
  - `README.md` — product overview, principles, layout, and stack.
  - `.gitignore` — central secret/exclusion rules for every stack in the monorepo.
  - `.gitattributes` — LF normalization and binary classification.
  - `.editorconfig` — cross-editor formatting defaults.
  - `CONTRIBUTING.md` — contribution workflow, standards, and review process.
  - `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1.
  - `SECURITY.md` — vulnerability disclosure and security requirements.
  - GitHub issue templates (bug report, feature request) and pull request template.
  - Monorepo directory scaffold: `apps/`, `backend/`, `packages/`, `docs/`,
    `scripts/`, `docker/`, `.github/` with per-directory README documentation.

### Changed

- Nothing yet — project initialized.

### Deprecated

- Nothing yet.

### Removed

- Nothing yet.

### Fixed

- Nothing yet.

### Security

- Repository policy established: secrets are never committed
  (see [SECURITY.md](./SECURITY.md)).
