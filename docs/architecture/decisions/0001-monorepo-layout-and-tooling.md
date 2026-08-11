# ADR-0001: Monorepo Layout and Tooling

## Status

- **Status:** Accepted
- **Date:** 2026-08-11
- **Deciders:** Maintainers

## Context

ANNEX spans four deliverable types — Flutter apps, a Flutter Web app, a React
browser extension, and a Python backend — that must share domain contracts and a
design system. The options considered were:

1. **Separate repositories per app** — clean isolation but guaranteed drift between
   client and server contracts, duplicated utilities, and cross-repo coordination
   overhead.
2. **Single repository with no tooling** — shared code is possible but the package
   dependency graph, versioning, and script orchestration become manual.
3. **Single monorepo with a Dart workspace tool** — shared packages with path
   dependencies, one review surface for cross-stack changes, and versioned internal
   libraries.

The Python backend and React extension do not fit Nx/Turborepo's Dart support, and
the Flutter ecosystem's standard workspace tool is Melos, making option 3 the only
choice that gives first-class support to the majority of the codebase.

## Decision

- Use a **single Git repository** at the project root with the structure defined in
  `README.md`: `apps/`, `backend/`, `packages/`, `docs/`, `scripts/`, `docker/`,
  `.github/`.
- Manage the Dart workspace with **Melos** (path dependencies between
  `packages/shared_*` and the Flutter apps; no registry publish needed).
- **Apps never depend on other apps.** Packages never import app code.
- Branch model: **GitHub Flow** on `main` with feature branches.
- Commits: **Conventional Commits**; versions: **Semantic Versioning** (2.0.0).

## Consequences

### Positive

- Atomic, reviewable changes across client and server (e.g., a contract change and
  its consumers land in one PR).
- One source of truth for domain contracts and design tokens.
- Shared CI, docs, and tooling config.

### Negative / Trade-offs

- Repository size and CI graph grow; a single clone includes all apps.
- Contributors must learn the monorepo conventions (documented in
  `CONTRIBUTING.md`).

### Neutral

- Release process is per-version (SemVer) rather than per-app.

## Compliance

- Directory contracts enforced by the README files in each directory.
- CI runs the repository validation script (`scripts/validate_repo.py`) on every
  change; Melos enforcement begins in Phase 8.
