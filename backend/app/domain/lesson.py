"""Education domain — media-literacy lessons with localized content (Phase 15).

Persisted into ``lessons`` / ``lesson_contents`` / ``lesson_progress``.
The aggregate carries the lesson metadata, its content resolved for the
best available locale in the fallback chain (ADR-0007), and the caller's
completion state so the API can render a lesson in one read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class LessonSection:
    """One content section within a localized lesson."""

    heading: str
    body: str
    bullets: tuple[str, ...] = ()


@dataclass(frozen=True)
class LessonContent:
    """Localized lesson content resolved for one locale."""

    locale_code: str
    title: str
    summary: str
    sections: tuple[LessonSection, ...] = ()


@dataclass(frozen=True)
class Lesson:
    """A published lesson with its resolved content and progress.

    Attributes:
        id: Primary key of the ``lessons`` row.
        slug: Stable URL identifier (unique).
        difficulty: ``beginner`` | ``intermediate`` | ``advanced``.
        category: Curriculum category (e.g. ``media_literacy``).
        estimated_minutes: Reading time estimate.
        order_index: Curriculum ordering.
        published: Whether the lesson is visible through the API.
        content: Content resolved for the best available chain locale,
            or None when the lesson has no content in any chain locale.
        completed: Whether the requesting user has completed the lesson.
        completed_at: When the user completed it, if completed.
    """

    id: UUID
    slug: str
    difficulty: str = "beginner"
    category: str = "media_literacy"
    estimated_minutes: int = 5
    order_index: int = 0
    published: bool = True
    content: LessonContent | None = None
    completed: bool = False
    completed_at: datetime | None = None


@dataclass(frozen=True)
class LessonProgress:
    """A user's completion record for one lesson."""

    lesson_id: UUID
    completed_at: datetime


def sections_from_json(rows: list[dict[str, Any]]) -> tuple[LessonSection, ...]:
    """Convert persisted ``sections`` JSONB rows into domain sections.

    Unknown keys in a section object are ignored so content can evolve
    without breaking older readers.
    """
    sections: list[LessonSection] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        headings = row.get("heading")
        bodies = row.get("body")
        if not isinstance(headings, str) or not isinstance(bodies, str):
            continue
        bullets = row.get("bullets")
        if not isinstance(bullets, list):
            bullets = []
        sections.append(
            LessonSection(
                heading=headings,
                body=bodies,
                bullets=tuple(str(item) for item in bullets),
            )
        )
    return tuple(sections)
