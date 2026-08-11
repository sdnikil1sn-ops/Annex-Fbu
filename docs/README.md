# `docs/` — Documentation Center

The single home for ANNEX documentation. Every guide, diagram, and decision record
lives here so that knowledge is findable, versioned, and reviewable in the same
repository as the code.

## Documentation index

| Document | Status | Phase |
|---|---|---|
| `architecture/overview.md` | Planned | 2 |
| `architecture/decisions/` (ADRs) | Planned | 2 |
| `architecture/diagrams/` (C4, sequence) | Planned | 2 |
| `database/schema.md` + ER diagram | Planned | 4 |
| `api/openapi.yaml` (generated) | Planned | 3 |
| `api/guide.md` | Planned | 3 |
| `guides/installation.md` | Planned | 2 |
| `guides/developer-guide.md` | Planned | 2 |
| `guides/deployment.md` | Planned | 11 |
| `guides/testing.md` | Planned | 2 |
| `guides/security.md` | Planned | 5 |
| `i18n/architecture.md` | Planned | 8 |
| `contributing/*` | — | See root `CONTRIBUTING.md` |

## Standards

- **Diagrams as code** — Mermaid/d2 source in `diagrams/` so diagrams stay
  diffable and reviewable.
- **ADR first** — significant architecture decisions are recorded as ADRs
  (`NNNN-title.md`) before implementation.
- **Docs follow code** — documentation ships in the same PR as the behavior it
  describes.

## Status

- **Phase 1:** directory reserved; index maintained here.
- **Phase 2:** architecture overview, ADRs, diagrams, and installation/developer
  guides are generated.
