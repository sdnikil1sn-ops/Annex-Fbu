# Runtime i18n Architecture

> **Status:** Accepted · **Phase:** 8 · **Scope:** Server-side translation delivery for every client
> **Related:** [ADR-0007](../architecture/decisions/0007-runtime-i18n.md), [API map](../api/v1-endpoints.md),
> [Schema design](../database/schema-design.md), [shared_utils key registry](../../packages/shared_utils/README.md)

ANNEX is **multilingual by architecture**: translations are served at runtime and
adding a language is a *data change*, never a rebuild. This document is the contract
behind that promise.

---

## 1. Principles

1. **Typed keys, never hardcoded prose.** Every user-facing string is a stable,
   dotted key (`common.cancel`, `analysis.submit`) registered in
   `shared_utils` (`StringKeys`). Hardcoded user-facing prose is rejected by lint
   once UI code lands (Phase 9+); the registry exists today so apps start typed.
2. **Translations live server-side.** `i18n_locales` + `i18n_translations`
   (migration 20260811000005, seed 20260812000003) are the single source of truth.
3. **Versioned bundles.** Clients fetch a bundle for a locale and cache it; a
   `version` (or ETag) tells them whether their copy is current — corrected
   translations reach users over the air without a release.
4. **Fallback chains.** `requested locale → parent locale → … → en`. A missing key
   resolves to the nearest parent that defines it; the base locale (English) always
   terminates the chain.

## 2. Data model

| Table | Purpose |
|---|---|
| `i18n_locales` | Enabled locales with `fallback_code` (the chain edge) |
| `i18n_translations` | `namespace`, `key`, `value`, `plural_rule`, `version` per locale |

One row per `(locale, namespace, key)`; `version` is bumped when a value changes so
bundle versions shift and clients refresh. `plural_rule` records the ICU category of
the stored form (`none` for plural-invariant strings); plural *expansion* stays
client-side with `intl`, so the server stores one canonical form per key.

## 3. API contract

### `GET /api/v1/i18n/locales` (public, 120/min)

```json
{
  "data": {
    "default_locale": "en",
    "locales": [
      { "code": "en", "fallback_code": null },
      { "code": "pt", "fallback_code": "en" }
    ]
  }
}
```

Clients use this to render a language picker and to build fallback chains locally
(e.g. `pt-BR → pt → en` when the server only declares `pt → en`).

### `GET /api/v1/i18n/bundles/{locale}?version=N` (public, 120/min)

```json
{
  "data": {
    "locale": "pt",
    "fallback_locale": "en",
    "version": 3,
    "entries": {
      "common.cancel": { "value": "Cancelar", "plural": "none" },
      "common.claims_count": { "value": "{count} alegações", "plural": "other" },
      "errors.generic": { "value": "Something went wrong. Please try again.", "plural": "none" }
    }
  },
  "meta": { "etag": "\"pt:3\"" }
}
```

- `entries` are **already resolved over the fallback chain**: Portuguese values win on
  their own keys; missing keys are filled from `en` (note `errors.generic` above).
  Clients do not re-implement fallback.
- `version` is the max entry version in the bundle. Pass it back as
  `?version=N` (or send the `ETag` in `If-None-Match`) to receive
  `304 Not Modified` while the bundle is unchanged.
- Responses carry `Cache-Control: public, max-age=<I18N_BUNDLE_CACHE_TTL>`
  (default 300 s) and a strong `ETag`.
- Unknown/disabled locales answer `404 i18n.locale_not_found`; malformed codes
  answer `400 validation.invalid_locale`.

## 4. Fallback chain resolution

The server merges a chain `[requested, parent, …, default]` from the most specific
to the least, keeping the **first** occurrence of each key:

```text
bundle("pt") with chain [pt, en]
  → common.cancel      = "Cancelar"   (pt)
  → common.claims_count = "{count} alegações"  (pt)
  → errors.generic     = "Something went wrong. Please try again."  (en)
```

The default locale is always appended last, so every chain terminates. Cycles in
declared fallbacks are broken by visiting each locale at most once. The same
algorithm ships client-side in `shared_utils` (`resolveFallbackChain`) for loading
states: while a bundle fetches, the UI falls back `requested → parent → en`.

## 5. Plural handling

- The backend stores one canonical plural form per key and records its ICU category
  in `plural_rule`.
- Clients select the category for a count with `intl` — or with the lightweight
  `shared_utils` `pluralCategory()` that covers the seeded languages (English
  one/other, French 0-and-1, Arabic zero/one/two/few/many/other, Russian
  one/few/many/other, CJK other).
- Full ICU plural variants (all categories per key) are a future enhancement; the
  schema's `plural_rule` column already names the category so the data model does
  not change when that lands.

## 6. RTL

Layouts are RTL-ready from the start (design-system requirement). Locale data is the
trigger: clients map the served locale to a text direction (`ar` → RTL) and flip
layouts without any rebuild. Server-side, RTL locales are ordinary locales.

## 7. Client behavior

1. On startup and on locale change, fetch `GET /i18n/locales`, then the bundle for
   the requested locale.
2. Cache the bundle locally (persisted). Send `?version=`/`If-None-Match` on refresh
   to get `304` when nothing changed.
3. While a bundle loads, resolve keys with the fallback chain (see §4). Never block
   the first paint on a bundle fetch — the chain provides usable English instantly.
4. Look up every user-facing string via `StringKeys`; missing keys must never render
   raw — fall back through the chain and, last resort, the key itself.

## 8. Adding a language

1. Add `en`-first keys to `StringKeys` in `shared_utils` (and the backend
   `i18n_translations` for the base locale).
2. Insert a row in `i18n_locales` with the proper `fallback_code`, then translation
   rows for the new locale (a migration or the admin data path).
3. The bundle endpoint serves the new locale immediately — no app release.

## 9. Lint rule (typed keys)

ADR-0007 mandates a lint rule blocking hardcoded user-facing strings in UI code.
There is no UI code in the monorepo yet (apps are scaffolds), so the rule ships with
the first UI phase (Phase 9+); the `StringKeys` registry it will enforce against is
already live and unit-tested.
