# Entity-Relationship Diagram — ANNEX Data Model

Logical data model (Phase 2 design). Full column definitions, constraints, indexes,
and RLS policies are specified in [../../database/schema-design.md](../../database/schema-design.md);
executable DDL ships with migrations in Phase 4.

```mermaid
erDiagram
    USERS ||--o| PROFILES : owns
    USERS ||--o{ USER_PREFERENCES : configures
    USERS ||--o{ ANALYSES : submits
    ANALYSES ||--o{ ANALYSIS_SCORES : scored_by
    ANALYSES ||--o{ CLAIMS : contains
    CLAIMS ||--o| CLAIM_VERDICTS : receives
    CLAIM_VERDICTS ||--o{ EVIDENCE : supported_by
    SOURCES ||--o{ CLAIMS : attributed_to
    SOURCES ||--o{ SOURCE_SCORES : rated_by
    ANALYSES ||--o{ MEDIA_ITEMS : includes
    MEDIA_ITEMS ||--o{ OCR_RESULTS : extracts
    MEDIA_ITEMS ||--o{ FORENSICS_REPORTS : inspected_by
    I18N_LOCALES ||--o{ I18N_TRANSLATIONS : contains

    USERS {
        uuid id PK "Firebase UID"
        text email UK
        text display_name
        text avatar_url
        timestamptz created_at
        timestamptz last_seen_at
    }

    PROFILES {
        uuid id PK
        uuid user_id FK
        text role "user | moderator | admin"
        text locale
        text country
        jsonb consent_flags
        timestamptz updated_at
    }

    USER_PREFERENCES {
        uuid id PK
        uuid user_id FK
        text default_locale
        text theme
        jsonb notifications
    }

    ANALYSES {
        uuid id PK
        uuid user_id FK "nullable: anonymous"
        text input_type "text | url | image"
        text status "pending | processing | completed | failed"
        text locale
        text failure_reason
        timestamptz created_at
        timestamptz completed_at
    }

    ANALYSIS_SCORES {
        uuid id PK
        uuid analysis_id FK
        text dimension
        numeric score "0.00 - 1.00"
        jsonb breakdown
    }

    CLAIMS {
        uuid id PK
        uuid analysis_id FK
        int claim_index
        text text
        text normalized_text
    }

    CLAIM_VERDICTS {
        uuid id PK
        uuid claim_id FK
        text verdict "verifiable | partially_verifiable | unverifiable | true | false | misleading"
        numeric confidence
        text model
        text model_version
        text rationale
        timestamptz created_at
    }

    EVIDENCE {
        uuid id PK
        uuid verdict_id FK
        text kind "link | quote | source"
        text url
        text quote
        text snippet
        numeric relevance
    }

    SOURCES {
        uuid id PK
        text domain UK
        text name
        text country
        text language
        text category
        timestamptz first_seen_at
        timestamptz updated_at
    }

    SOURCE_SCORES {
        uuid id PK
        uuid source_id FK
        numeric score "0.00 - 1.00"
        jsonb signals
        text model
        timestamptz computed_at
    }

    MEDIA_ITEMS {
        uuid id PK
        uuid analysis_id FK
        text storage_path
        text mime
        text sha256
        int width
        int height
        bigint size_bytes
        timestamptz ingested_at
    }

    OCR_RESULTS {
        uuid id PK
        uuid media_item_id FK
        text language
        numeric confidence
        text raw_text
        jsonb boxes
        timestamptz created_at
    }

    FORENSICS_REPORTS {
        uuid id PK
        uuid media_item_id FK
        jsonb signals
        numeric risk_score
        text model
        timestamptz created_at
    }

    I18N_LOCALES {
        uuid id PK
        text code UK "e.g. en, pt-BR"
        bool enabled
        text fallback_code
    }

    I18N_TRANSLATIONS {
        uuid id PK
        uuid locale_id FK
        text namespace
        text key
        text value
        text plural_rule
        int version
        timestamptz updated_at
    }
```
