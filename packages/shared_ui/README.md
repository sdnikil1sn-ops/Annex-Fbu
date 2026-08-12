# `packages/shared_ui/` — ANNEX Design System (Flutter)

The shared Flutter design system used by `apps/mobile` and `apps/web`. It is the
single source of truth for how ANNEX looks and feels.

## Planned contents (implemented in Phase 8)

```text
shared_ui/
├── lib/
│   ├── tokens/               # Colors, typography, spacing, radii, motion
│   ├── components/           # Buttons, cards, score meters, claim widgets
│   ├── layout/               # Adaptive scaffolds, navigation
│   ├── feedback/             # Snackbars, banners, inline error states
│   └── accessibility/        # Contrast tokens, semantics helpers, focus guides
├── test/                     # Widget + golden tests
└── pubspec.yaml
```

## Design requirements

- **Tokens first** — components consume design tokens; raw values never appear in
  components.
- **Dark & light themes** derived from the same token set.
- **Accessible by default** — WCAG 2.1 AA contrast, full `Semantics` support,
  keyboard/focus navigation.
- **Localization-aware** — RTL-ready layouts and text-direction handling.
- **Documented components** — every public widget has a doc comment and a widget
  test.

## Status

- **Phase 1:** package documented and reserved.
- **Phase 8:** token foundation, core components, accessibility layer.
- **Phase 9 (done):** shipped with the mobile app — tokens (colors, spacing,
  typography), light/dark themes, and core components (`AppButton`,
  `ScoreMeter`, `ClaimCard`, `StatusPill`) with widget tests (9).
