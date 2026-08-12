"""Runtime i18n service (ADR-0007).

Resolves versioned translation bundles from the repository: the requested
locale's entries, merged over its fallback chain so missing keys are
filled from the nearest parent and ultimately the default locale. The
bundle version is the max entry version, which clients use for
conditional requests (``304 Not Modified``).
"""

from __future__ import annotations

from app.application.ports.repositories import I18nRepository
from app.domain.i18n import (
    I18nLocale,
    ResolvedBundle,
    merge_entries,
    resolve_fallback_chain,
)


class I18nService:
    """Coordinates locale listing and bundle resolution.

    Args:
        repository: The i18n persistence port.
        default_locale: The fallback-chain root (usually ``en``).
    """

    def __init__(self, repository: I18nRepository, *, default_locale: str = "en") -> None:
        self._repository = repository
        self._default_locale = default_locale

    @property
    def default_locale(self) -> str:
        """The fallback-chain root locale code."""
        return self._default_locale

    def list_locales(self) -> list[I18nLocale]:
        """Return every enabled locale with its fallback parent."""
        return self._repository.list_locales()

    def bundle(self, locale: str) -> ResolvedBundle | None:
        """Resolve a fully merged bundle for a locale code.

        Args:
            locale: Requested locale code (case-insensitive).

        Returns:
            The resolved bundle, or None when the locale is unknown or
            disabled (the API answers 404).
        """
        code = locale.strip().lower()
        locales = {entry.code: entry for entry in self._repository.list_locales()}
        if code not in locales:
            return None

        chain = resolve_fallback_chain(code, locales, self._default_locale)
        entries_by_locale = {item: self._repository.translations_for(item) for item in chain}
        entries = merge_entries(entries_by_locale)
        version = max((entry.version for entry in entries.values()), default=1)
        fallback_locale = chain[1] if len(chain) > 1 else None
        return ResolvedBundle(
            locale=code,
            fallback_locale=fallback_locale,
            version=version,
            entries=entries,
        )
