# C4 — Container Diagram (Level 2)

The major deployable containers and their relationships. Canonical source for the
level-2 view.

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        M["Mobile App<br/>Flutter<br/>(Android · iOS · Win · Linux · macOS)"]
        W["Web App<br/>Flutter Web + PWA"]
        E["Browser Extension<br/>React + TS (MV3)"]
    end

    subgraph Backend["Backend (Cloud Run)"]
        API["API Service<br/>FastAPI"]
        WK["Worker Service<br/>Celery"]
    end

    subgraph Data["Data Plane"]
        PG[("PostgreSQL<br/>Supabase")]
        OBJ[("Object Storage<br/>Supabase")]
        RD[("Redis")]
    end

    subgraph External["External Services"]
        FA["Firebase Auth"]
        AI["OpenAI / Gemini"]
        OCR["Tesseract OCR"]
        CV["OpenCV"]
    end

    M --> API
    W --> API
    E --> API
    API --> PG
    API --> OBJ
    API --> FA
    API --> RD
    API --> AI
    API -->|"enqueue jobs"| WK
    WK --> PG
    WK --> OBJ
    WK --> OCR
    WK --> CV
    WK --> AI
```

## Container responsibilities

| Container | Tech | Responsibility | Key rules |
|---|---|---|---|
| Mobile / Web app | Flutter | Feature UI, sign-in, offline caching | Talks only to Backend API |
| Browser extension | React + TS | In-page verification | Never holds secrets |
| API Service | FastAPI | Validation, authn/authz, orchestration, API surface | Thin routes (ADR-0003) |
| Worker Service | Celery | OCR/forensics/LLM pipelines | Idempotent tasks (ADR-0008) |
| PostgreSQL | Supabase | Primary store, RLS | Accessed via repositories only |
| Object Storage | Supabase | Media blobs | Signed URLs, short expiry |
| Redis | Redis | Broker, rate limits, caches | Shared by API + workers |
| Firebase Auth / OpenAI / Gemini / Tesseract / OpenCV | External / libs | Identity, LLM, OCR, forensics | Never contacted by clients |
