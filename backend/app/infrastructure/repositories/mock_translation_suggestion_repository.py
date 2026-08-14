"""In-memory TranslationSuggestionRepository for unit tests (explicit mock)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.ports.repositories import TranslationSuggestionRepository
from app.domain.i18n import (
    SUGGESTION_APPROVED,
    SUGGESTION_PENDING,
    MissingKey,
    TranslationSuggestion,
)


class MockTranslationSuggestionRepository(TranslationSuggestionRepository):
    """A deterministic in-memory store implementing the suggestion port.

    Mirrors the PostgreSQL shape: pending suggestions are unique per
    (user, locale, key) — a re-submission updates the existing pending
    row — and only pending rows can be reviewed. ``seed_translations``
    provides the default-locale key set so ``list_missing`` matches the
    seed migration's shape.
    """

    def __init__(self) -> None:
        self._suggestions: dict[UUID, TranslationSuggestion] = {}
        # Known/disabled mirror of i18n_locales (code -> enabled).
        self._locales: dict[str, bool] = {"en": True, "pt": True, "es": True}
        # (locale, namespace, key) -> translation value (i18n_translations).
        self._entries: dict[tuple[str, str, str], str] = {}

    # --- seeding helpers for tests ---------------------------------------

    def add_locale(self, code: str, *, enabled: bool = True) -> None:
        """Register an enabled/disabled locale (mirrors i18n_locales)."""
        self._locales[code] = enabled

    def seed_translation(
        self, locale: str, namespace: str, key: str, value: str
    ) -> None:
        """Register a translation row (used to derive missing keys)."""
        self._entries[(locale, namespace, key)] = value

    def seed_suggestion(
        self,
        locale: str,
        namespace: str,
        key: str,
        value: str,
        suggested_by: UUID,
        *,
        status: str = SUGGESTION_PENDING,
    ) -> TranslationSuggestion:
        """Pre-populate a suggestion in a given state."""
        suggestion = TranslationSuggestion(
            id=uuid4(),
            locale_code=locale,
            namespace=namespace,
            key=key,
            value=value,
            suggested_by=suggested_by,
            status=status,
            created_at=datetime.now(UTC),
        )
        self._suggestions[suggestion.id] = suggestion
        return suggestion

    # --- port implementation ---------------------------------------------

    def list_missing(
        self, locale_code: str, default_locale: str = "en"
    ) -> list[MissingKey]:
        """Keys defined for the default locale but missing for the target."""
        missing: list[MissingKey] = []
        for (locale, namespace, key), value in sorted(self._entries.items()):
            if locale == default_locale and (locale_code, namespace, key) not in self._entries:
                missing.append(
                    MissingKey(namespace=namespace, key=key, english_value=value)
                )
        return missing

    def submit(self, suggestion: TranslationSuggestion) -> TranslationSuggestion | None:
        """Insert or update the contributor's own pending row.

        Returns None when the target locale has no default entries (the
        mock treats an empty locale registry as 'unknown locale').
        """
        if not self._locales.get(suggestion.locale_code):
            return None

        for existing in self._suggestions.values():
            if (
                existing.locale_code == suggestion.locale_code
                and existing.namespace == suggestion.namespace
                and existing.key == suggestion.key
                and existing.suggested_by == suggestion.suggested_by
                and existing.status == SUGGESTION_PENDING
            ):
                updated = TranslationSuggestion(
                    id=existing.id,
                    locale_code=existing.locale_code,
                    namespace=existing.namespace,
                    key=existing.key,
                    value=suggestion.value,
                    plural_rule=suggestion.plural_rule,
                    suggested_by=existing.suggested_by,
                    status=existing.status,
                    created_at=existing.created_at,
                )
                self._suggestions[existing.id] = updated
                return updated

        created = TranslationSuggestion(
            id=uuid4(),
            locale_code=suggestion.locale_code,
            namespace=suggestion.namespace,
            key=suggestion.key,
            value=suggestion.value,
            plural_rule=suggestion.plural_rule,
            suggested_by=suggestion.suggested_by,
            status=SUGGESTION_PENDING,
            created_at=datetime.now(UTC),
        )
        self._suggestions[created.id] = created
        return created

    def get(self, suggestion_id: UUID) -> TranslationSuggestion | None:
        return self._suggestions.get(suggestion_id)

    def list_for_user(
        self, user_id: UUID, *, status: str | None = None
    ) -> list[TranslationSuggestion]:
        suggestions = [
            item
            for item in self._suggestions.values()
            if item.suggested_by == user_id and (status is None or item.status == status)
        ]
        return sorted(
            suggestions,
            key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )

    def list_pending(self, *, limit: int = 50) -> list[TranslationSuggestion]:
        pending = [
            item
            for item in self._suggestions.values()
            if item.status == SUGGESTION_PENDING
        ]
        return sorted(
            pending, key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC)
        )[:limit]

    def review(
        self, suggestion_id: UUID, reviewer_id: UUID, approved: bool
    ) -> TranslationSuggestion | None:
        existing = self._suggestions.get(suggestion_id)
        if existing is None or existing.status != SUGGESTION_PENDING:
            return None
        reviewed = TranslationSuggestion(
            id=existing.id,
            locale_code=existing.locale_code,
            namespace=existing.namespace,
            key=existing.key,
            value=existing.value,
            plural_rule=existing.plural_rule,
            suggested_by=existing.suggested_by,
            status=SUGGESTION_APPROVED if approved else "rejected",
            created_at=existing.created_at,
            reviewed_by=reviewer_id,
            reviewed_at=datetime.now(UTC),
        )
        self._suggestions[suggestion_id] = reviewed
        return reviewed
