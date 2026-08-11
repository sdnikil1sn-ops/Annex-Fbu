# ANNEX

> **Learn Before You Believe.**

**ANNEX** is a production-grade, open-source, AI-powered **Media & Information Literacy**
platform. It helps people verify the trustworthiness of news articles, claims, images,
and sources *before* they share them — combining large-language-model analysis, OCR,
image forensics, and source credibility scoring with structured media-literacy education.

| | |
|---|---|
| **Status** | Foundation (Phase 1) — in active development |
| **License** | [Apache-2.0](./LICENSE) |
| **Version** | 0.1.0 (see [CHANGELOG](./CHANGELOG.md)) |
| **Platforms** | Android · iOS · Web · Windows · Linux · macOS · Browser extensions |
| **Stack** | Flutter · FastAPI · Supabase (PostgreSQL + Storage) · Firebase Auth · OpenAI/Gemini · Redis · Celery · Docker |

---

## Why ANNEX

Misinformation moves faster than correction. ANNEX meets users where they consume
content and gives them the tools to *learn before they believe*:

- **Claim analysis** — paste or share any text; ANNEX decomposes claims, scores
  verifiability, and surfaces supporting or contradicting evidence.
- **Media forensics** — OCR (Tesseract) and image analysis (OpenCV) detect manipulated
  or out-of-context images and extract text for verification.
- **Source credibility scoring** — a transparent, explainable model rates publishers,
  authors, and domains across multiple trust signals.
- **Media literacy education** — interactive lessons, checklists, and inline guidance
  that teach *how* to verify, not just *what* to believe.
- **Browser extension** — verify articles, images, and claims without leaving the page.

## Product principles

1. **Transparency first** — every score explains itself; no black-box verdicts.
2. **Multilingual by architecture** — unlimited languages, translations never require a rebuild.
3. **Privacy-preserving** — minimal data collection, user control over analysis history.
4. **Open source, open standards** — Apache-2.0, OpenAPI contracts, portable data.

## Monorepo layout

```text
annex/
├── apps/
│   ├── mobile/            # Flutter app — Android, iOS, Windows, Linux, macOS
│   ├── web/               # Flutter Web entry, PWA, Firebase Hosting config
│   └── extension/         # React + TypeScript browser extension (MV3)
├── backend/               # FastAPI service layer + Celery workers
├── packages/
│   ├── shared_ui/         # Flutter design system (tokens, components, a11y)
│   ├── shared_models/     # Domain models + JSON Schema contracts
│   └── shared_utils/      # Pure-Dart utilities (validation, i18n, formatting)
├── docs/                  # Architecture, API, database, deployment guides
├── scripts/               # Cross-platform automation
├── docker/                # Images and local-development compose files
└── .github/               # Issue/PR templates, CI/CD workflows
```

## Tech stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | Flutter 3.x (Dart 3.x) | Single codebase, six platforms |
| Browser extension | React + TypeScript | Manifest V3, Chrome/Edge/Firefox |
| Backend | FastAPI (Python 3.14) | Service-layer architecture, OpenAPI-first |
| Database | Supabase PostgreSQL | Row-level security, managed backups |
| Storage | Supabase Storage | Media assets with signed URLs |
| Auth | Firebase Authentication | Google, Apple, email, anonymous |
| AI | OpenAI, Gemini (optional) | Claims, summarization, embeddings |
| OCR | Tesseract | Text extraction from images |
| Image processing | OpenCV | Forensics, manipulation detection |
| Cache | Redis | Sessions, rate-limit counters, hot data |
| Background jobs | Celery | Analysis pipelines, OCR, enrichment |
| Containers | Docker | Dev compose + production images |
| Deployment | GitHub Actions, Firebase Hosting, Cloud Run | CI/CD per commit |

## Getting started

> Detailed instructions land in later phases. The repository is currently in
> **Phase 1 (Foundation)** — no application code exists yet.

- [Installation guide](docs/installation.md) — *scheduled for Phase 2*
- [Developer guide](docs/developer-guide.md) — *scheduled for Phase 2*
- [Deployment guide](docs/deployment.md) — *scheduled for Phase 11*

See [docs/README.md](docs/README.md) for the full documentation index.

## Contributing

We welcome contributors. Please read [CONTRIBUTING.md](./CONTRIBUTING.md) first — it
covers the coding standards (Clean Architecture, SOLID, DRY, KISS), commit conventions,
and the review process. All participants are expected to follow our
[Code of Conduct](./CODE_OF_CONDUCT.md).

## Security

Found a vulnerability? **Do not open a public issue.** Follow the disclosure process in
[SECURITY.md](./SECURITY.md).

## License

Copyright 2026 ANNEX Contributors. Released under the
[Apache License, Version 2.0](./LICENSE).
