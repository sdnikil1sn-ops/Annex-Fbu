# `scripts/` — Automation

Cross-platform automation scripts for building, testing, linting, and releasing
ANNEX. Scripts keep developer commands consistent across machines and CI.

## Current scripts

| Script | Purpose |
|---|---|
| [`validate_repo.py`](./validate_repo.py) | Repository health: YAML syntax, markdown links, required files, secret patterns. Runs locally and in CI (`ci.yml`). |

## Planned scripts (added with their targets)

```text
scripts/
├── bootstrap.sh / .ps1       # First-time setup (deps, env templates) — Phase 3
├── dev.sh / .ps1             # Local dev stack (backend + redis + workers) — Phase 7
├── lint.sh / .ps1            # Run all linters/formatters — Phase 3
├── test.sh / .ps1            # Run all test suites — Phase 3
├── build.sh / .ps1           # Build targets for all apps — Phase 8
└── release.sh / .ps1         # Version bump + changelog + tag — Phase 11
```

## Rules

- Every script is idempotent and safe to re-run.
- Scripts never contain secrets; they read from environment variables or `.env`.
- Each script is mirrored for POSIX (`.sh`) and Windows (`.ps1`) where practical,
  with identical behavior.
- `scripts/` is the only place repo-level automation lives; CI workflows call
  these scripts rather than duplicating logic (DRY).
