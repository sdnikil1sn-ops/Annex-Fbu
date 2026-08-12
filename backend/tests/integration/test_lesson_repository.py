"""Integration tests: PostgresLessonRepository against a real database.

Lessons and their content are seeded by migrations 20260812000005 and
20260812000006, which are applied by helpers.apply_migrations on every
run (i18n_locales seed 20260812000003 provides the locale registry).
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from app.application.ports.repositories import LessonRepository
from app.infrastructure.repositories.lesson_repository import PostgresLessonRepository

from tests.integration.helpers import apply_migrations, create_user

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> LessonRepository:
    """A fresh-schema Postgres lesson repository per test (seeded)."""
    apply_migrations(TEST_DSN)
    return PostgresLessonRepository(TEST_DSN)


def test_list_lessons_returns_seeded_curriculum(repository: LessonRepository) -> None:
    """The seed migration populates four published lessons in order."""
    lessons = repository.list_lessons(chain=["en"])
    assert [lesson.slug for lesson in lessons] == [
        "spotting-misinformation",
        "understanding-credibility-scores",
        "verifying-images",
        "analyzing-claims",
    ]
    first = lessons[0]
    assert first.content is not None
    assert first.content.locale_code == "en"
    assert first.content.title == "Spotting Misinformation"
    assert first.content.sections
    assert first.content.sections[0].bullets


def test_list_lessons_resolves_portuguese_content(repository: LessonRepository) -> None:
    """A pt chain picks the pt variant; other lessons fall back to en."""
    lessons = repository.list_lessons(chain=["pt", "en"])
    assert lessons[0].content is not None
    assert lessons[0].content.locale_code == "pt"
    assert lessons[0].content.title == "Como Detectar Desinformação"

    assert lessons[1].content is not None
    assert lessons[1].content.locale_code == "en"
    assert lessons[1].content.title == "Understanding Credibility Scores"


def test_get_lesson_returns_none_for_unknown(repository: LessonRepository) -> None:
    """An unknown lesson id yields None, not an error."""
    assert repository.get_lesson(uuid4(), chain=["en"]) is None


def test_get_by_slug_finds_lesson(repository: LessonRepository) -> None:
    """Lessons are addressable by their stable slug."""
    lesson = repository.get_by_slug("verifying-images", chain=["en"])
    assert lesson is not None
    assert lesson.category == "media_literacy"
    assert lesson.estimated_minutes == 8


def test_mark_complete_is_idempotent_and_owner_scoped(
    repository: LessonRepository,
) -> None:
    """Completion persists per user; re-completion keeps the first time."""
    user_id = uuid4()
    create_user(TEST_DSN, user_id)
    lesson_id = repository.list_lessons(chain=["en"])[0].id

    first = repository.mark_complete(user_id, lesson_id)
    second = repository.mark_complete(user_id, lesson_id)
    assert first.completed_at == second.completed_at

    # The completing user sees progress; a different user does not.
    other_user = uuid4()
    create_user(TEST_DSN, other_user)
    owned = repository.get_lesson(lesson_id, chain=["en"], user_id=user_id)
    assert owned is not None and owned.completed is True
    foreign = repository.get_lesson(lesson_id, chain=["en"], user_id=other_user)
    assert foreign is not None and foreign.completed is False
