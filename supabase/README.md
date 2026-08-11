# `supabase/` — Database & Storage

Supabase project assets: versioned PostgreSQL migrations and (from Phase 4)
the storage policies. The logical schema is documented in
[`docs/database/schema-design.md`](../docs/database/schema-design.md).

## Migrations

Versioned SQL files in `migrations/` (`YYYYMMDDHHMMSS_name.sql`). They are applied
in filename order and must be **additive where possible**; destructive changes ship
as explicit `drop` migrations with review.

| Migration | Contents |
|---|---|
| `20260811000001_core_tables.sql` | users, profiles, user_preferences, analyses, analysis_scores |
| `20260811000002_claims.sql` | claims, claim_verdicts, evidence |
| `20260811000003_sources.sql` | sources, source_scores |
| `20260811000004_media.sql` | media_items, ocr_results, forensics_reports |
| `20260811000005_i18n.sql` | i18n_locales, i18n_translations |
| `20260811000006_rls.sql` | Row-Level Security policies for every table |

## Applying migrations

Requires the [Supabase CLI](https://supabase.com/docs/guides/cli) (not installed
on this machine yet — install via `scoop install supabase` / `brew install
supabase` when a hosted project is linked):

```bash
supabase init            # creates config.toml (once)
supabase link --project-ref <project-ref>
supabase db push         # apply pending migrations
supabase db reset        # recreate the local database from migrations
```

The integration test suite applies the migrations itself against any PostgreSQL
(see `backend/tests/integration/`), so development does not require the CLI.

## Storage (from Phase 4/6)

Buckets: `media` (analysis uploads) and `avatars`. Policies enforce least
privilege; objects are served via short-expiry signed URLs. Bucket policies are
added as a later migration.
