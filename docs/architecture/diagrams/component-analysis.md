# Component Diagram — Analysis Pipeline

Component-level view of the backend's analysis pipeline, showing the layering from
ADR-0003 (api → application → infrastructure ports → adapters) and the async handoff
from ADR-0008.

```mermaid
flowchart TB
    R["AnalysisRouter<br/>(api · v1)"] --> S["AnalysisService<br/>(application)"]
    S --> O["AnalysisOrchestrator<br/>(application)"]
    O --> Q["AnalysisQueue<br/>(Celery producer)"]
    O --> A["AIAnalyzerPort<br/>(port)"]
    O --> OCR["OcrAdapterPort<br/>(port)"]
    O --> FV["ForensicsAdapterPort<br/>(port)"]
    A --> P1["OpenAI Adapter"]
    A --> P2["Gemini Adapter (optional)"]
    OCR --> T["Tesseract"]
    FV --> C["OpenCV"]
    S --> AR["AnalysisRepository"]
    S --> CR["ClaimRepository"]
    S --> MR["MediaRepository"]
    AR --> PG[("PostgreSQL")]
    CR --> PG
    MR --> OBJ[("Object Storage")]
    Q --> WK["Worker (Celery)"]
    WK --> A
    WK --> OCR
    WK --> FV
```

## Layer rules in this diagram

- Routers depend only on services; services depend on ports and repositories.
- Adapters (OpenAI, Gemini, Tesseract, OpenCV, Supabase) are swappable behind ports.
- The worker reuses the same ports as the orchestrator — one implementation of the
  guarded AI calls, exercised from both request-scoped and job-scoped paths.
- Guard layer (ADR-0006) wraps every port implementation; not shown for clarity.
