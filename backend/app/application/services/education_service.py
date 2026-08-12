"""Education service — the media-literacy curriculum (Phase 15).

Coordinates lesson reads with locale resolution (ADR-0007): the user's
locale is expanded into its fallback chain (requested → parent → …
→ default) and handed to the repository, which picks the best content
for that chain. Completion is an idempotent upsert per (user, lesson).
"""

from __future__ import annotations

from uuid import UUID

from app.application.ports.repositories import I18nRepository, LessonRepository
from app.domain.i18n import resolve_fallback_chain
from app.domain.lesson import Lesson, LessonProgress


class EducationService:
    """Coordinates curriculum reads and progress.

    Args:
        repository: The lesson persistence port.
        i18n_repository: The locale registry used to expand fallback
            chains (ADR-0007); the same port the i18n service uses.
        default_locale: The fallback-chain root (usually ``en``).
    """

    def __init__(
        self,
        repository: LessonRepository,
        i18n_repository: I18nRepository,
        *,
        default_locale: str = "en",
    ) -> None:
        self._repository = repository
        self._i18n_repository = i18n_repository
        self._default_locale = default_locale

    def list_lessons(self, locale: str, user_id: UUID | None = None) -> list[Lesson]:
        """Return the published curriculum for a locale."""
        return self._repository.list_lessons(
            chain=self._chain(locale),
            user_id=user_id,
        )

    def get_lesson(
        self, lesson_id: UUID, locale: str, user_id: UUID | None = None
    ) -> Lesson | None:
        """Fetch one lesson with chain-resolved content and progress."""
        return self._repository.get_lesson(
            lesson_id,
            chain=self._chain(locale),
            user_id=user_id,
        )

    def get_by_slug(
        self, slug: str, locale: str, user_id: UUID | None = None
    ) -> Lesson | None:
        """Fetch one lesson by its stable slug."""
        return self._repository.get_by_slug(
            slug,
            chain=self._chain(locale),
            user_id=user_id,
        )

    def mark_complete(self, user_id: UUID, lesson_id: UUID) -> LessonProgress:
        """Record a lesson completion idempotently."""
        return self._repository.mark_complete(user_id, lesson_id)

    # --- internals -------------------------------------------------------

    def _chain(self, locale: str) -> list[str]:
        """Expand a locale code into its ordered fallback chain.

        Unknown or blank locales fall back to the default locale so the
        curriculum is always readable.
        """
        code = (locale or "").strip().lower() or self._default_locale
        locales = {entry.code: entry for entry in self._i18n_repository.list_locales()}
        if code not in locales:
            code = self._default_locale
        return resolve_fallback_chain(code, locales, self._default_locale)
