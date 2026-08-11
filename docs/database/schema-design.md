# ANNEX — Database Schema Design

> Phase 2 logical design. Executable DDL is delivered as versioned Supabase
> migrations in Phase 4. ER view: [er-diagram.md](../architecture/diagrams/er-diagram.md).

## Principles

1. **All tables have `id uuid primary key default gen_random_uuid()`** unless stated.
2. **Timestamps** are `timestamptz`, UTC, named `created_at` / `updated_at` /
   `completed_at` as appropriate.
3. **RLS is enabled on every user-data table** (ADR-0004); policies use
   `auth.uid()` as the row owner key.
4. **Soft deletion** (`deleted_at`) for GDPR erasure flows; hard deletes run in
   worker jobs after grace periods.
5. **Enum-ish strings** are validated by CHECK constraints (portable) rather than
   Postgres `ENUM` types unless a type is reused across many tables.

## Tables

### `users`

Identity mirror keyed by Firebase UID (ADR-0005).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | = Firebase UID |
| email | text | UNIQUE | Lower-cased |
| display_name | text | | |
| avatar_url | text | | |
| created_at | timestamptz | NOT NULL default now() | |
| last_seen_at | timestamptz | | Updated on API activity |

RLS: `id = auth.uid()` (select/update own row).

### `profiles`

One-to-one with `users`; holds role and consent.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users, UNIQUE | |
| role | text | CHECK in (user, moderator, admin) default 'user' | RBAC source of truth (ADR-0005) |
| locale | text | default 'en' | Current UI language |
| country | text | | ISO 3166-1 alpha-2 |
| consent_flags | jsonb | default '{}' | Analytics/data-usage consent |
| updated_at | timestamptz | NOT NULL default now() | |

### `user_preferences`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users, UNIQUE | |
| default_locale | text | default 'en' | |
| theme | text | CHECK in (system, light, dark) default 'system' | |
| notifications | jsonb | default '{}' | Channel toggles |

### `analyses`

One row per submitted analysis request (ADR-0008 state machine).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| user_id | uuid | FK → users, NULLABLE | NULL = anonymous |
| input_type | text | CHECK in (text, url, image) | |
| status | text | CHECK in (pending, processing, completed, failed) | State machine (ADR-0008) |
| locale | text | default 'en' | Analysis language |
| failure_reason | text | | Structured error code on `failed` |
| created_at | timestamptz | NOT NULL default now() | |
| completed_at | timestamptz | | Set on terminal state |

Indexes: `(user_id, created_at desc)`, `(status)`, `(id)` for polling.

### `analysis_scores`

Dimensional score breakdown of an analysis.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| analysis_id | uuid | FK → analyses | |
| dimension | text | e.g. claim_verifiability, source_reliability, media_integrity | |
| score | numeric(3,2) | CHECK 0.00–1.00 | |
| breakdown | jsonb | | Per-dimension explanation payload |

Unique `(analysis_id, dimension)`.

### `claims`

Claims extracted from an analysis input.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| analysis_id | uuid | FK → analyses | |
| claim_index | int | | Order within analysis |
| text | text | NOT NULL | Original wording |
| normalized_text | text | | Normalized for matching |

Unique `(analysis_id, claim_index)`.

### `claim_verdicts`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| claim_id | uuid | FK → claims | |
| verdict | text | CHECK in (verifiable, partially_verifiable, unverifiable, true, false, misleading) | |
| confidence | numeric(3,2) | CHECK 0.00–1.00 | |
| model | text | | Provider + model name |
| model_version | text | | |
| rationale | text | | Human-readable explanation |
| created_at | timestamptz | NOT NULL default now() | |

### `evidence`

Evidence supporting a verdict.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| verdict_id | uuid | FK → claim_verdicts | |
| kind | text | CHECK in (link, quote, source) | |
| url | text | | |
| quote | text | | |
| snippet | text | | |
| relevance | numeric(3,2) | CHECK 0.00–1.00 | |

### `sources`

Publisher/domain registry.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| domain | text | UNIQUE, NOT NULL | Canonical domain |
| name | text | | Publisher name |
| country | text | | |
| language | text | | |
| category | text | | news, blog, government, … |
| first_seen_at | timestamptz | default now() | |
| updated_at | timestamptz | NOT NULL default now() | |

### `source_scores`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| source_id | uuid | FK → sources | |
| score | numeric(3,2) | CHECK 0.00–1.00 | |
| signals | jsonb | | Named trust signals |
| model | text | | |
| computed_at | timestamptz | NOT NULL default now() | |

### `media_items`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| analysis_id | uuid | FK → analyses | |
| storage_path | text | NOT NULL | Supabase Storage object path |
| mime | text | | |
| sha256 | text | | Content fingerprint |
| width / height | int | | |
| size_bytes | bigint | | |
| ingested_at | timestamptz | default now() | |

### `ocr_results`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| media_item_id | uuid | FK → media_items | |
| language | text | | Detected script/language |
| confidence | numeric(3,2) | | |
| raw_text | text | | |
| boxes | jsonb | | Word/line bounding boxes |
| created_at | timestamptz | NOT NULL default now() | |

### `forensics_reports`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| media_item_id | uuid | FK → media_items | |
| signals | jsonb | | ELA, metadata, C2PA, duplication, … |
| risk_score | numeric(3,2) | | |
| model | text | | |
| created_at | timestamptz | NOT NULL default now() | |

### `i18n_locales` / `i18n_translations`

Runtime i18n (ADR-0007).

`i18n_locales`: `id`, `code` (UNIQUE, e.g. `en`, `pt-BR`), `enabled` (bool),
`fallback_code` (text, e.g. `pt-BR → pt → en`).

`i18n_translations`:

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | uuid | PK | |
| locale_id | uuid | FK → i18n_locales | |
| namespace | text | | feature/domain namespace |
| key | text | | Stable typed key |
| value | text | | Translated string |
| plural_rule | text | | ICU plural form or `none` |
| version | int | default 1 | Bumped on change (bundle versioning) |
| updated_at | timestamptz | NOT NULL default now() | |

Unique `(locale_id, namespace, key)`.

## RLS policy matrix

| Table | Policy |
|---|---|
| users, profiles, user_preferences | `auth.uid() = id / user_id` (owner) |
| analyses, analysis_scores, claims, claim_verdicts, evidence | Owner via `user_id`; public read only where `anonymous` allowed |
| sources, source_scores | Public read; writes via service role only |
| media_items, ocr_results, forensics_reports | Owner read; writes via service role |
| i18n_* | Public read; writes via service role |
