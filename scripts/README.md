# `scripts/` — Automation

Cross-platform automation scripts for building, testing, linting, and releasing
ANNEX. Scripts keep developer commands consistent across machines and CI.

## Planned contents (implemented across phases)

```text
scripts/
├── bootstrap.sh / .ps1       # First-time setup (deps, env templates)
├── dev.sh / .ps1             # Local dev stack (backend + redis + workers)
├── lint.sh / .ps1            # Run all linters/formatters
├── test.sh / .ps1            # Run all test suites
├── build.sh / .ps1           # Build targets for all apps
└── release.sh / .ps1         # Version bump + changelog + tag
```

## Rules

- Every script is idempotent and safe to re-run.
- Scripts never contain secrets; they read from environment variables or `.env`.
- Each script is mirrored for POSIX (`.sh`) and Windows (`.ps1`) where practical,
  with identical behavior.
- `scripts/` is the only place repo-level automation lives; CI workflows call
  these scripts rather than duplicating logic (DRY).

## Status

- **Phase 1:** directory reserved.
- Scripts are added as their targets exist (backend in Phase 3, Flutter in Phase 8,
  extension in Phase 10, release in Phase 11).
