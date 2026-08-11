# `docs/` — Documentation Center

The single home for ANNEX documentation. Every guide, diagram, and decision record
lives here so that knowledge is findable, versioned, and reviewable in the same
repository as the code.

## Documentation index

| Document | Status | Phase |
|---|---|---|
| `architecture/overview.md` | ✅ Created | 2 |
| `architecture/decisions/` (ADRs) | ✅ Created — template + 8 ADRs | 2 |
| `architecture/diagrams/` | ✅ Created — C4, component, sequence, ER | 2 |
| `api/v1-endpoints.md` | ✅ Created | 2 |
| `api/openapi.yaml` (generated) | ✅ Generated via `scripts/generate_openapi.py` | 3 |
| `database/schema-design.md` | ✅ Created | 2 |
| `database/migrations/` (DDL) | Planned — Supabase CLI | 4 |
| `guides/installation.md` | ✅ Created | 2 |
| `guides/developer-guide.md` | ✅ Created | 2 |
| `guides/testing.md` | ✅ Created | 2 |
| `guides/security.md` | Planned | 5 |
| `guides/deployment.md` | Planned | 11 |
| `i18n/architecture.md` | Planned | 8 |

## Standards

- **Diagrams as code** — Mermaid source in `architecture/diagrams/` so diagrams stay
  diffable and reviewable (rendered by GitHub).
- **ADR first** — significant architecture decisions are recorded as ADRs
  (`NNNN-title.md`) before implementation; see the template.
- **Docs follow code** — documentation ships in the same PR as the behavior it
  describes.
- **Links are validated** — `scripts/validate_repo.py` fails CI on broken internal
  links, so the index never rots.
