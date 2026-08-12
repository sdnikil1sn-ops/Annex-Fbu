"""In-memory LessonRepository for unit tests (explicit mock)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.ports.repositories import LessonRepository
from app.domain.lesson import Lesson, LessonContent, LessonProgress, LessonSection

_EN = "en"
_PT = "pt"


def _seed_content() -> dict[tuple[str, str], LessonContent]:
    """Content keyed by (slug, locale), mirroring the seed migration."""
    return {
        ("spotting-misinformation", _EN): LessonContent(
            locale_code=_EN,
            title="Spotting Misinformation",
            summary="Learn to recognize the common patterns behind misleading content.",
            sections=(
                LessonSection(
                    heading="Why misinformation spreads",
                    body="Misinformation spreads faster than corrections.",
                    bullets=("Emotional headlines are a red flag", "Check before you share"),
                ),
            ),
        ),
        ("spotting-misinformation", _PT): LessonContent(
            locale_code=_PT,
            title="Como Detectar Desinformação",
            summary="Aprenda a reconhecer os padrões comuns.",
            sections=(
                LessonSection(
                    heading="Por que a desinformação se espalha",
                    body="A desinformação se espalha mais rápido que correções.",
                    bullets=("Títulos emocionais são um sinal de alerta",),
                ),
            ),
        ),
        ("understanding-credibility-scores", _EN): LessonContent(
            locale_code=_EN,
            title="Understanding Credibility Scores",
            summary="How ANNEX scores sources and what the numbers mean.",
            sections=(),
        ),
    }


class MockLessonRepository(LessonRepository):
    """A deterministic in-memory store implementing the lesson port.

    Metadata lives per slug; content lives per (slug, locale) exactly like
    ``lesson_contents``. ``resolve`` picks the content whose locale appears
    earliest in the caller's fallback chain (ADR-0007) and attaches the
    caller's completion state.
    """

    def __init__(self, seed: list[Lesson] | None = None) -> None:
        self._by_slug: dict[str, Lesson] = {lesson.slug: lesson for lesson in (seed or _SEED_META)}
        self._content = dict(_seed_content())
        self._progress: dict[tuple[UUID, UUID], datetime] = {}

    def list_lessons(
        self, *, chain: list[str], user_id: UUID | None = None
    ) -> list[Lesson]:
        """Published lessons ordered by curriculum position."""
        return sorted(
            (self._resolve(lesson, chain, user_id) for lesson in self._by_slug.values()),
            key=lambda lesson: lesson.order_index,
        )

    def get_lesson(
        self, lesson_id: UUID, *, chain: list[str], user_id: UUID | None = None
    ) -> Lesson | None:
        """Fetch one lesson by id."""
        for lesson in self._by_slug.values():
            if lesson.id == lesson_id:
                return self._resolve(lesson, chain, user_id)
        return None

    def get_by_slug(
        self, slug: str, *, chain: list[str], user_id: UUID | None = None
    ) -> Lesson | None:
        """Fetch one lesson by its stable slug."""
        lesson = self._by_slug.get(slug)
        return self._resolve(lesson, chain, user_id) if lesson else None

    def mark_complete(self, user_id: UUID, lesson_id: UUID) -> LessonProgress:
        """Record a completion idempotently (first timestamp wins)."""
        key = (user_id, lesson_id)
        if key not in self._progress:
            self._progress[key] = datetime.now(UTC)
        return LessonProgress(lesson_id=lesson_id, completed_at=self._progress[key])

    # --- internals -------------------------------------------------------

    def _resolve(self, lesson: Lesson, chain: list[str], user_id: UUID | None) -> Lesson:
        """Attach the best-chain-locale content and the user's progress."""
        completed_at = self._progress.get((user_id, lesson.id)) if user_id else None
        return Lesson(
            id=lesson.id,
            slug=lesson.slug,
            difficulty=lesson.difficulty,
            category=lesson.category,
            estimated_minutes=lesson.estimated_minutes,
            order_index=lesson.order_index,
            published=lesson.published,
            content=self._best_content(lesson.slug, chain),
            completed=completed_at is not None,
            completed_at=completed_at,
        )

    def _best_content(self, slug: str, chain: list[str]) -> LessonContent | None:
        """Return the content whose locale appears earliest in the chain."""
        candidates = [
            content for (c_slug, _locale), content in self._content.items() if c_slug == slug
        ]
        ranked = sorted(
            (content for content in candidates if content.locale_code in chain),
            key=lambda content: chain.index(content.locale_code),
        )
        return ranked[0] if ranked else None


# Lesson metadata mirroring the seed migration (content is in _seed_content).
_SEED_META: list[Lesson] = [
    Lesson(
        id=uuid4(),
        slug="spotting-misinformation",
        difficulty="beginner",
        category="media_literacy",
        estimated_minutes=5,
        order_index=1,
    ),
    Lesson(
        id=uuid4(),
        slug="understanding-credibility-scores",
        difficulty="intermediate",
        category="source_credibility",
        estimated_minutes=7,
        order_index=2,
    ),
]
