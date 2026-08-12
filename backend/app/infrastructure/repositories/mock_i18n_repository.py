"""In-memory I18nRepository for unit tests (explicit mock).

Lives behind the same port as the PostgreSQL implementation and is never
used in production code paths. ``MockI18nRepository.seeded()`` mirrors the
seed migration's shape so tests exercise realistic fallback chains.
"""

from __future__ import annotations

from app.application.ports.repositories import I18nRepository
from app.domain.i18n import I18nLocale, TranslationEntry

# English — the fallback root. Other locales define a subset and rely on
# the chain to fill the rest (same contract as the seed migration).
_SEED_LOCALES = [
    I18nLocale(code="en"),
    I18nLocale(code="pt", fallback_code="en"),
    I18nLocale(code="es", fallback_code="en"),
]

_SEED_TRANSLATIONS: dict[str, list[TranslationEntry]] = {
    "en": [
        TranslationEntry("common", "cancel", "Cancel"),
        TranslationEntry("common", "save", "Save"),
        TranslationEntry("common", "retry", "Retry"),
        TranslationEntry("common", "learn_before_you_believe", "Learn before you believe."),
        TranslationEntry("analysis", "submit", "Analyze"),
        TranslationEntry("analysis", "summary", "Summary"),
        TranslationEntry("auth", "sign_in", "Sign in"),
        TranslationEntry("errors", "generic", "Something went wrong. Please try again."),
    ],
    "pt": [
        TranslationEntry("common", "cancel", "Cancelar"),
        TranslationEntry("common", "save", "Salvar"),
        TranslationEntry("analysis", "submit", "Analisar"),
    ],
    "es": [
        TranslationEntry("common", "cancel", "Cancelar"),
        TranslationEntry("analysis", "submit", "Analizar"),
    ],
}


class MockI18nRepository(I18nRepository):
    """A deterministic in-memory store implementing the repository port."""

    def __init__(
        self,
        *,
        locales: list[I18nLocale] | None = None,
        translations: dict[str, list[TranslationEntry]] | None = None,
    ) -> None:
        self._locales = {locale.code: locale for locale in (locales or [])}
        self._translations = {code: list(entries) for code, entries in (translations or {}).items()}

    @classmethod
    def seeded(cls) -> MockI18nRepository:
        """Build a store with the seed migration's representative shape."""
        return cls(locales=list(_SEED_LOCALES), translations=_SEED_TRANSLATIONS)

    def list_locales(self) -> list[I18nLocale]:
        """Return all configured locales (the mock stores only enabled)."""
        return list(self._locales.values())

    def translations_for(self, locale_code: str) -> list[TranslationEntry]:
        """Return the configured entries for a locale code."""
        return list(self._translations.get(locale_code, []))

    def add_locale(self, code: str, fallback_code: str | None = None) -> None:
        """Register an enabled locale (test helper)."""
        self._locales[code] = I18nLocale(code=code, fallback_code=fallback_code)

    def add_translation(
        self,
        locale_code: str,
        namespace: str,
        key: str,
        value: str,
        *,
        plural_rule: str = "none",
        version: int = 1,
    ) -> None:
        """Register one translation (test helper)."""
        entry = TranslationEntry(namespace, key, value, plural_rule, version)
        self._translations.setdefault(locale_code, []).append(entry)
