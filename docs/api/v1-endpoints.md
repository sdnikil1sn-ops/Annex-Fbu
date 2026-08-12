# ANNEX API — v1 Endpoint Map

> Phase 2 design. The executable OpenAPI specification (`openapi.yaml`) is generated
> from the FastAPI application in Phase 3; this document is the human contract for
> what v1 must expose.

## General conventions

| Concern | Convention |
|---|---|
| Base path | `/api/v1` (versioned prefix; breaking changes → new major version, ADR-0002) |
| Authentication | Firebase ID token in `Authorization: Bearer <token>`; verified server-side (ADR-0005) |
| Anonymous access | Public endpoints are explicitly listed; everything else requires a verified token |
| Response envelope | `{ "data": ..., "meta": {...} }` for success; `{ "error": { "code", "message", "request_id" } }` for failure |
| Error codes | Machine-readable codes (`auth.expired_token`, `validation.invalid_input`, `validation.invalid_url`, `validation.invalid_image`, `analysis.not_found`, `analysis.fetch_failed`, `analysis.media_failed`, `rate.exceeded`, …) |
| Pagination | Cursor-based: `?cursor=...&limit=50`; `meta.next_cursor` returned |
| Idempotency | State-changing analysis endpoints accept `Idempotency-Key` headers |
| Tracing | Every response includes `X-Request-ID`; log lines carry it |
| Rate limits | Redis-backed (ADR-0008); limits documented per endpoint below |

## System

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/health` | none | none | Liveness (always 200) |
| GET | `/health/ready` | none | none | Readiness (DB/Redis reachable) |
| GET | `/api/v1/meta/version` | none | 120/min | API version + commit SHA |

## Auth

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| POST | `/api/v1/auth/session/verify` | token | 60/min | Server-side verification + profile hydration |
| DELETE | `/api/v1/auth/session` | token | 60/min | Sign out everywhere (client revokes) |

> Sign-in itself is handled by Firebase SDKs on the client; the backend never sees
> passwords (ADR-0005).

## Users

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/users/me` | token | 120/min | Current profile + preferences |
| PATCH | `/api/v1/users/me` | token | 60/min | Update profile (name, locale, country) |
| PATCH | `/api/v1/users/me/preferences` | token | 60/min | Update preferences (theme, notifications) |
| GET | `/api/v1/users/me/history` | token | 60/min | Analysis history (paginated) |
| DELETE | `/api/v1/users/me` | token | 10/min | GDPR erase (soft-delete + job purge) |

## Analysis

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| POST | `/api/v1/analysis` | token or anon | 20/min | Submit text/URL/image; returns 202 + `analysis_id` |
| GET | `/api/v1/analysis/{id}` | owner | 120/min | Poll status / fetch report |
| GET | `/api/v1/analysis` | owner | 60/min | List own analyses (cursor paginated) |
| DELETE | `/api/v1/analysis/{id}` | owner | 30/min | Delete an analysis + its media |

## Claims

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/claims/{id}` | owner | 120/min | Claim + verdict + evidence |
| GET | `/api/v1/claims/{id}/evidence` | owner | 120/min | Evidence links for a verdict |

## Sources

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/sources/{domain}` | token or anon | 60/min | Source profile + credibility score |
| GET | `/api/v1/sources/search?q=` | token or anon | 60/min | Search sources by name/domain |

## Media

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| POST | `/api/v1/media` | token or anon | 20/min | Upload image (multipart); returns signed URL + `media_id` |
| POST | `/api/v1/media/{id}/analyze` | token or anon | 20/min | Enqueue OCR + forensics for an uploaded image |
| GET | `/api/v1/media/{id}` | owner | 120/min | Media metadata + OCR + forensics report |

## Education

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/lessons` | token | 60/min | Lesson list (localized) |
| GET | `/api/v1/lessons/{id}` | token | 120/min | Lesson content (localized) |
| POST | `/api/v1/lessons/{id}/complete` | token | 30/min | Mark lesson complete (progress) |

## i18n

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/i18n/locales` | none | 120/min | Enabled locales + fallback chain |
| GET | `/api/v1/i18n/bundles/{locale}?version=` | none | 120/min | Versioned translation bundle (ADR-0007) |

## Submit contract for `POST /analysis`

Exactly one content field must be present, matching `input_type`:

| `input_type` | Field | Notes |
|---|---|---|
| `text` | `text` (≤ 20 000 chars) | Analyzed directly |
| `url` | `url` (≤ 2 048 chars) | Fetched server-side through the SSRF guard; report carries `media.input` (`url`, `final_url`, `status`) |
| `image` | `image` (base64 or `data:` URL) | Decoded with a size cap; MIME is sniffed from the bytes; OCR + forensics run; report carries `media.ocr` + `media.forensics` |

URLs must be plain http(s) without embedded credentials (shape-checked at
the boundary; DNS/IP validation happens in the fetcher). Images are capped
at `MEDIA_IMAGE_MAX_BYTES` (default 4 MB decoded). A refused URL fails the
analysis with `analysis.fetch_failed`; an undecodable image fails with
`analysis.media_failed` — both are FAILED states clients can surface, never
5xx responses.

## Status model for analyses

`pending → processing → completed | failed` (ADR-0008). `meta.retry_after` is
included while pending/processing so clients can poll politely.
