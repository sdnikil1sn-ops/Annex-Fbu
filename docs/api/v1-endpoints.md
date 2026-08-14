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
| Error codes | Machine-readable codes (`auth.expired_token`, `validation.invalid_input`, `validation.invalid_url`, `validation.invalid_image`, `analysis.not_found`, `analysis.fetch_failed`, `analysis.media_failed`, `claim.not_found`, `source.not_found`, `media.not_found`, `media.analysis_not_found`, `lesson.not_found`, `rate.exceeded`, …) |
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

> Implemented in Phase 14. Claims are persisted when their analysis
> completes; reads are owner-scoped.

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/claims/{id}` | owner | 120/min | Claim + verdict + evidence |
| GET | `/api/v1/claims/{id}/evidence` | owner | 120/min | Evidence links for a verdict |

## Sources

> Implemented in Phase 14. The publisher/domain registry is public-read
> (RLS policy matrix); profiles carry the latest credibility score.

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/sources/{domain}` | none | 60/min | Source profile + credibility score |
| GET | `/api/v1/sources/search?q=` | none | 60/min | Search sources by name/domain |

## Media

> Implemented in Phase 14. Images are submitted as base64 (or `data:` URL)
> in a JSON body; OCR + forensics run synchronously during ingest. Reads
> are owner-scoped through the owning analysis.

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| POST | `/api/v1/media` | owner | 20/min | Ingest an image for an owned analysis; runs OCR + forensics; returns the media record |
| GET | `/api/v1/media/{id}` | owner | 120/min | Media metadata + OCR + forensics report |

## Education

> Implemented in Phase 15. The media-literacy curriculum: lesson metadata,
> localized content (resolved through the caller's locale fallback chain,
> ADR-0007), and idempotent per-user completion. All routes require a
> token — progress is per-user and content renders in the user's locale.

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| GET | `/api/v1/lessons` | token | 60/min | Lesson list (localized, with progress) |
| GET | `/api/v1/lessons/{id or slug}` | token | 120/min | Lesson content + sections (localized) |
| POST | `/api/v1/lessons/{id or slug}/complete` | token | 30/min | Mark lesson complete (idempotent) |

> `{id or slug}` accepts either the lesson UUID or its stable slug (e.g.
> `spotting-misinformation`) so clients can deep-link with human-readable
> URLs. Content resolves through the caller's locale fallback chain; an
> optional `?locale=` query parameter overrides the profile locale for all
> three endpoints. Completing a lesson twice keeps the original timestamp
> (the first completion wins). An unknown lesson reference answers
> `lesson.not_found`.

## Classes (educator tools)

> Implemented in Phase 17. Any authenticated user can create a class
> (becoming its teacher) and invite students with the generated invite
> code; teachers assign published lessons and read class-wide completion
> progress. Progress is derived from `lesson_progress` (Phase 15), so
> there is no separate progress store. Authorization is enforced at the
> service boundary — calls from non-members/non-teachers answer
> `class.not_found` and never reveal whether a class exists.

| Method | Path | Auth | Rate limit | Purpose |
|---|---|---|---|---|
| POST | `/api/v1/classes` | token | 30/min | Create a class; the caller becomes its teacher |
| GET | `/api/v1/classes` | member | 60/min | List the caller's classes (owned or joined) with role |
| GET | `/api/v1/classes/{id}` | member | 120/min | Class detail with the member roster |
| POST | `/api/v1/classes/{id}/join` | token | 30/min | Join by invite code (idempotent) |
| POST | `/api/v1/classes/{id}/assignments` | teacher | 30/min | Assign a published lesson (by UUID or slug) |
| GET | `/api/v1/classes/{id}/assignments` | member | 60/min | Assignments with completion stats |
| GET | `/api/v1/classes/{id}/progress` | teacher | 60/min | Per-assignment, per-student completion |
| GET | `/api/v1/classes/{id}/assignments/{assignment_id}/progress` | teacher | 60/min | Per-student completion for one assignment |
| DELETE | `/api/v1/classes/{id}/assignments/{assignment_id}` | teacher | 30/min | Unassign a lesson |
| DELETE | `/api/v1/classes/{id}/members/{member_id}` | teacher | 30/min | Remove a student |
| DELETE | `/api/v1/classes/{id}` | owner | 10/min | Delete a class (members + assignments cascade) |

> Invite codes are 8 characters from an unambiguous alphabet
> (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789`). Assignments are unique per
> (class, lesson): re-assigning the same lesson is idempotent and returns
> the existing assignment. An unknown lesson reference answers
> `lesson.not_found`; an unknown class (or a teacher-only call from a
> non-teacher) answers `class.not_found`. The class service is optional
> at the server level — when unconfigured, every classes route answers
> `classes.not_configured` (503).

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

## Submit contract for `POST /media`

| Field | Notes |
|---|---|
| `analysis_id` | UUID of an analysis owned by the caller |
| `image` | base64 or `data:` URL, same decoding rules as `POST /analysis` |

The image is decoded (size-capped), then OCR (Tesseract) + tamper
forensics (OpenCV) run synchronously during ingest; the 201 response
carries the media record with its `ocr` and `forensics` children. A
missing/foreign analysis fails with `media.analysis_not_found` (404); an
undecodable image fails with `validation.invalid_image`.

## Status model for analyses

`pending → processing → completed | failed` (ADR-0008). `meta.retry_after` is
included while pending/processing so clients can poll politely.
