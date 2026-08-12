"""Unit tests for the EducationService (Phase 15)."""

from __future__ import annotations

from uuid import uuid4

from app.application.services.education_service import EducationService
from app.infrastructure.repositories.mock_i18n_repository import MockI18nRepository
from app.infrastructure.repositories.mock_lesson_repository import MockLessonRepository


def _service() -> EducationService:
    return EducationService(
        MockLessonRepository(),
        MockI18nRepository.seeded(),
        default_locale="en",
    )


def test_list_lessons_resolves_english_content() -> None:
    """A user with the default locale gets the English curriculum."""
    service = _service()
    lessons = service.list_lessons(locale="en")
    assert [lesson.slug for lesson in lessons] == [
        "spotting-misinformation",
        "understanding-credibility-scores",
    ]
    first = lessons[0]
    assert first.content is not None
    assert first.content.locale_code == "en"
    assert first.content.title == "Spotting Misinformation"


def test_list_lessons_uses_pt_content_when_available() -> None:
    """A pt user gets the pt variant where it exists."""
    service = _service()
    lessons = service.list_lessons(locale="pt")
    first = lessons[0]
    assert first.content is not None
    assert first.content.locale_code == "pt"
    assert first.content.title == "Como Detectar Desinformação"


def test_list_lessons_falls_back_to_english_without_pt() -> None:
    """Lessons without a pt variant resolve through the chain to en."""
    service = _service()
    lessons = service.list_lessons(locale="pt")
    second = lessons[1]
    assert second.content is not None
    assert second.content.locale_code == "en"
    assert second.content.title == "Understanding Credibility Scores"


def test_unknown_locale_falls_back_to_default() -> None:
    """An unknown locale code resolves to the default chain."""
    service = _service()
    lessons = service.list_lessons(locale="xx-unknown")
    assert all(lesson.content is not None for lesson in lessons)
    assert lessons[0].content.locale_code == "en"


def test_get_lesson_returns_content_and_sections() -> None:
    """get_lesson returns the aggregate with chain-resolved content."""
    service = _service()
    lesson = service.get_lesson(service.list_lessons("en")[0].id, locale="en")
    assert lesson is not None
    assert lesson.slug == "spotting-misinformation"
    assert lesson.content is not None
    assert lesson.content.sections
    assert lesson.content.sections[0].heading == "Why misinformation spreads"
    assert lesson.content.sections[0].bullets


def test_get_lesson_returns_none_for_unknown() -> None:
    """An unknown lesson id yields None (the API turns it into 404)."""
    service = _service()
    assert service.get_lesson(uuid4(), locale="en") is None


def test_mark_complete_is_idempotent() -> None:
    """Re-completing keeps the original completion timestamp."""
    service = _service()
    user_id = uuid4()
    lesson_id = service.list_lessons("en")[0].id

    first = service.mark_complete(user_id, lesson_id)
    second = service.mark_complete(user_id, lesson_id)

    assert first.completed_at == second.completed_at
    assert second.lesson_id == lesson_id


def test_completion_visible_in_list_and_get() -> None:
    """Marked lessons surface completed state in subsequent reads."""
    service = _service()
    user_id = uuid4()
    lesson_id = service.list_lessons("en")[0].id

    service.mark_complete(user_id, lesson_id)

    listed = service.list_lessons("en", user_id=user_id)
    assert listed[0].completed is True
    assert listed[0].completed_at is not None
    assert listed[1].completed is False

    fetched = service.get_lesson(lesson_id, locale="en", user_id=user_id)
    assert fetched is not None
    assert fetched.completed is True


def test_unauthenticated_reads_show_no_completion() -> None:
    """Without a user id, lessons are never reported completed."""
    service = _service()
    lessons = service.list_lessons("en")
    assert all(lesson.completed is False for lesson in lessons)
