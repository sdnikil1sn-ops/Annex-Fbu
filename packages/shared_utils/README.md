# `packages/shared_utils/` — Shared Utilities (Pure Dart)

Pure-Dart helper utilities shared by all apps and packages. No Flutter imports, no
platform channels — code here must run anywhere Dart runs.

## Planned contents (implemented in Phase 8)

```text
shared_utils/
├── lib/
│   ├── text/                 # Normalization, URL parsing, claim cleanup
│   ├── validation/           # Email, URL, language-tag validators
│   ├── format/               # Date, number, duration formatting
│   ├── i18n/                 # Key registry, locale resolution, plural rules
│   └── result/               # Result/error primitives shared by services
├── test/                     # Unit tests with high coverage
└── pubspec.yaml
```

## Rules

- **Zero dependencies on app code** — only Dart SDK (and, where justified, small
  pure-Dart packages).
- Every function documented; edge cases tested.
- Utilities must be deterministic and locale-aware where formatting is involved.

## Status

- **Phase 1:** package documented and reserved.
- **Phase 8:** initial utility set with tests.
