# `packages/shared_models/` — Domain Models & Contracts

The canonical domain models of ANNEX. This package defines the data shapes that
cross the app/API boundary, implemented as Dart classes for the Flutter clients
with JSON serialization compatible with the backend's OpenAPI contracts.

## Planned contents (implemented in Phase 8)

```text
shared_models/
├── lib/
│   ├── claim.dart            # Claim, ClaimVerdict, EvidenceLink
│   ├── analysis.dart         # AnalysisRequest, AnalysisReport, ScoreBreakdown
│   ├── source.dart           # PublisherProfile, SourceScore, DomainReport
│   ├── media.dart            # MediaItem, OcrResult, ForensicsReport
│   ├── user.dart             # UserProfile, Preference, HistoryEntry
│   └── i18n.dart             # Locale, TranslationBundle, LanguageTag
├── contracts/                # Canonical JSON Schema (single source of truth)
├── test/                     # Serialization round-trip tests
└── pubspec.yaml
```

## Contract strategy

1. Canonical JSON Schema lives in `contracts/` — one source of truth.
2. Dart models are (ideally) generated from those schemas, keeping clients and
   backend in lockstep.
3. The FastAPI backend derives its Pydantic models from the **same** OpenAPI spec,
   so a contract change is reviewable in one place.
4. Versioning: models are additive-friendly; breaking changes bump the package
   version and are coordinated across the Melos workspace.

## Rules

- Models are **pure Dart** — no Flutter imports, no UI logic.
- Serialization must be deterministic and strictly validated (unknown fields
  rejected at the API boundary).
- Every model has a doc comment and a round-trip serialization test.

## Status

- **Phase 1:** package documented and reserved.
- **Phase 8:** first model versions + codegen pipeline.
- **Phase 9 (done):** analysis, i18n, and user models matching the backend
  contract, with strict JSON round-trip tests (14). Codegen pipeline
  (from OpenAPI/JSON Schema) remains a follow-up.
