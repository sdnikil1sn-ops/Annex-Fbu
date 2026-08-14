"""Translation suggestion service — community translations (Phase 18).

Coordinates the review queue: contributors propose translations for
keys a target locale has not translated yet, moderators approve or
reject, and an approved suggestion is published into
``i18n_translations`` through the I18nRepository — the version bump
makes bundles refresh over the air (ADR-0007). Authorization is
enforced at the API boundary (moderator role gate); the service
validates domain rules (enabled locale, pending-only review) and
returns None for anything the caller cannot do, which the API turns
into 404-style answers that never leak state.
"""

from __future__ import annotations

from uuid import UUID

from app.application.ports.repositories import (
    I18nRepository,
    TranslationSuggestionRepository,
)
from app.domain.i18n import (
    SUGGESTION_PENDING,
    MissingKey,
    TranslationSuggestion,
)


class TranslationSuggestionService:
    """Coordinates community translation submission and review.

    Args:
        repository: The suggestion review queue port (Phase 18).
        i18n_repository: The live translation store — used to publish
            approved suggestions and to resolve enabled locales.
    """

    def __init__(
        self,
        repository: TranslationSuggestionRepository,
        i18n_repository: I18nRepository,
    ) -> None:
        self._repository = repository
        self._i18n_repository = i18n_repository

    def missing(self, locale_code: str, default_locale: str = "en") -> list[MissingKey]:
        """Return untranslated keys for a locale.

        Locales outside the enabled set resolve to an empty list — the
        contributor cannot translate what clients cannot consume.
        """
        if not self._locale_enabled(locale_code):
            return []
        return self._repository.list_missing(locale_code, default_locale)

    def submit(
        self,
        user_id: UUID,
        locale_code: str,
        namespace: str,
        key: str,
        value: str,
        plural_rule: str = "none",
    ) -> TranslationSuggestion | None:
        """Submit a translation proposal.

        Returns None when the locale is unknown or disabled. Re-submitting
        the same key updates the contributor's own pending suggestion
        (idempotent per user + locale + key).
        """
        if not self._locale_enabled(locale_code):
            return None
        return self._repository.submit(
            TranslationSuggestion(
                locale_code=locale_code,
                namespace=namespace.strip(),
                key=key.strip(),
                value=value.strip(),
                plural_rule=plural_rule,
                suggested_by=user_id,
                status=SUGGESTION_PENDING,
            )
        )

    def list_for_user(
        self, user_id: UUID, *, status: str | None = None
    ) -> list[TranslationSuggestion]:
        """Return a contributor's suggestions, newest first."""
        return self._repository.list_for_user(user_id, status=status)

    def list_pending(self, *, limit: int = 50) -> list[TranslationSuggestion]:
        """Return the moderator review queue, oldest first."""
        return self._repository.list_pending(limit=limit)

    def review(
        self, suggestion_id: UUID, reviewer_id: UUID, approved: bool
    ) -> TranslationSuggestion | None:
        """Approve or reject a pending suggestion.

        Returns None when the suggestion does not exist or was already
        reviewed (a suggestion changes status exactly once). An approved
        suggestion is published into ``i18n_translations`` — the bundle
        version bumps so clients pick the new value up without a release.
        """
        suggestion = self._repository.get(suggestion_id)
        if suggestion is None or suggestion.status != SUGGESTION_PENDING:
            return None
        if approved:
            self._i18n_repository.publish_translation(
                suggestion.locale_code,
                suggestion.namespace,
                suggestion.key,
                suggestion.value,
                suggestion.plural_rule,
            )
        return self._repository.review(suggestion_id, reviewer_id, approved)

    # --- internals -------------------------------------------------------

    def _locale_enabled(self, locale_code: str) -> bool:
        """True when the locale code is in the enabled set."""
        code = locale_code.strip().lower()
        return any(
            entry.code == code for entry in self._i18n_repository.list_locales()
        )
