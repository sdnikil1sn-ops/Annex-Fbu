# `packages/shared_utils/` — Shared Utilities (Pure Dart)

Pure-Dart helper utilities shared by all apps and packages. No Flutter imports, no
platform channels — code here must run anywhere Dart runs.

## Planned contents (implemented in Phase 8)

```text
shared_utils/
├── lib/
│   ├── text/                 # Normalization, URL parsing, claim cleanup   (planned)
│   ├── validation/           # Language-tag validator                     (done)
│   ├── format/               # Date, number, duration formatting          (planned)
│   ├── i18n/                 # Key registry, locale resolution, plurals  (done)
│   └── result/               # Result/error primitives shared by services (planned)
├── test/                     # Unit tests with high coverage
└── pubspec.yaml
```

## Implemented (Phase 8)

- **`i18n/string_keys.dart`** — the typed string-key registry (ADR-0007):
  stable `namespace.key` constants for every user-facing string, key
  validation, and namespace lookup. Hardcoded user-facing prose is
  forbidden by the project i18n lint rule (ships with the first UI phase).
- **`i18n/locale_resolver.dart`** — fallback-chain resolution
  (`requested → parent → … → default`) mirroring the backend algorithm,
  cycle-safe, for loading states and offline fallback.
- **`i18n/plural_rules.dart`** — ICU plural category selection for the
  seeded languages (one/other, French, Arabic, Slavic, CJK).
- **`validation/language_tag.dart`** — BCP-47-style locale-tag validation
  matching the backend contract.

All utilities are covered by unit tests (`dart test`).

## Rules

- **Zero dependencies on app code** — only Dart SDK (and, where justified, small
  pure-Dart packages).
- Every function documented; edge cases tested.
- Utilities must be deterministic and locale-aware where formatting is involved.

## Status

- **Phase 1:** package documented and reserved.
- **Phase 8 (done):** i18n key registry, locale resolution, plural rules,
  and language-tag validation with unit tests (ADR-0007).
