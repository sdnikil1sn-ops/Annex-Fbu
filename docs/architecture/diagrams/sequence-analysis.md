# Sequence Diagram — Analysis Request

End-to-end trace of a user submitting content for analysis. Shows the async handoff
(202 + polling) from ADR-0008 and where the guarded AI/OCR/forensics work runs.

```mermaid
sequenceDiagram
    actor U as User
    participant C as Client (App / Web / Extension)
    participant A as FastAPI (API Service)
    participant S as AnalysisService
    participant DB as PostgreSQL
    participant Q as Celery (Redis broker)
    participant W as Worker
    participant X as AI / OCR / OpenCV adapters

    U->>C: Submit text / URL / image
    C->>A: POST /v1/analysis (Bearer ID token)
    A->>A: Verify ID token · validate input · rate limit
    A->>S: analysis_service.submit(request)
    S->>DB: INSERT analyses (status=pending)
    S->>Q: enqueue job (analysis_id)
    S-->>A: accepted
    A-->>C: 202 { analysis_id, status: pending }

    Q->>W: dispatch job
    W->>DB: UPDATE analyses (status=processing)
    W->>X: OCR + forensics (image) / parse (text)
    X-->>W: signals + extracted text
    W->>X: claim analysis (guarded prompts)
    X-->>W: verdicts + scores
    W->>DB: INSERT claims/verdicts/evidence/scores
    W->>DB: UPDATE analyses (status=completed)
    W-->>Q: job complete

    C->>A: GET /v1/analysis/{id} (poll)
    A->>S: analysis_service.get_report(id)
    S->>DB: read report
    A-->>C: 200 full report (scores + evidence)
    C-->>U: Render explainable score breakdown
```

## Notes

- All arrows from `C` to `A` carry a verified Firebase ID token (ADR-0005).
- The worker path is **idempotent**: a re-delivered job re-checks `analysis_id`
  before writing (ADR-0008).
- If any step fails: `status=failed` with a structured error; the client renders a
  retry affordance.
