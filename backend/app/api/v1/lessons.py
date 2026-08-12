"""Education endpoints — v1 contract (Phase 15).

The media-literacy curriculum: a localized lesson list, per-lesson
content (resolved through the caller's locale fallback chain), and
idempotent completion progress. All routes require a verified token —
progress is per-user, and the curriculum renders in the user's locale.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from app.api.deps import get_current_user, get_education_service_dep
from app.api.errors import AppError
from app.application.services.education_service import EducationService
from app.domain.lesson import Lesson, LessonSection
from app.domain.user import User

router = APIRouter(prefix="/lessons", tags=["lessons"])


def _section_payload(section: LessonSection) -> dict[str, Any]:
    return {
        "heading": section.heading,
        "body": section.body,
        "bullets": list(section.bullets),
    }


def _resolve_lesson(
    lesson_ref: str, user: User, service: EducationService
) -> Lesson | None:
    """Resolve a lesson reference that is either a UUID or a stable slug."""
    try:
        lesson_id = UUID(lesson_ref)
    except ValueError:
        return service.get_by_slug(lesson_ref, locale=user.locale, user_id=user.id)
    return service.get_lesson(lesson_id, locale=user.locale, user_id=user.id)


def _lesson_payload(lesson: Lesson, *, detail: bool = False) -> dict[str, Any]:
    content = lesson.content
    payload: dict[str, Any] = {
        "id": str(lesson.id),
        "slug": lesson.slug,
        "difficulty": lesson.difficulty,
        "category": lesson.category,
        "estimated_minutes": lesson.estimated_minutes,
        "order_index": lesson.order_index,
        "title": content.title if content else None,
        "summary": content.summary if content else None,
        "completed": lesson.completed,
        "completed_at": lesson.completed_at.isoformat() if lesson.completed_at else None,
    }
    if detail:
        payload["locale"] = content.locale_code if content else None
        payload["sections"] = (
            [_section_payload(section) for section in content.sections] if content else []
        )
    return payload


@router.get("")
def list_lessons(
    user: User = Depends(get_current_user),
    service: EducationService = Depends(get_education_service_dep),
) -> dict[str, Any]:
    """Return the published curriculum, localized for the caller."""
    lessons = service.list_lessons(locale=user.locale, user_id=user.id)
    return {"data": [_lesson_payload(lesson) for lesson in lessons]}


@router.get("/{lesson_ref}")
def get_lesson(
    lesson_ref: str = Path(pattern=r"[0-9a-f-]{36}|[a-z0-9-]{1,100}"),
    user: User = Depends(get_current_user),
    service: EducationService = Depends(get_education_service_dep),
) -> dict[str, Any]:
    """Fetch one lesson with its localized content and progress.

    ``lesson_ref`` accepts either the lesson UUID or its stable slug
    (e.g. ``spotting-misinformation``), so clients can deep-link with
    human-readable URLs.
    """
    lesson = _resolve_lesson(lesson_ref, user, service)
    if lesson is None:
        raise AppError("lesson.not_found", "Lesson not found.", status_code=404)
    return {"data": _lesson_payload(lesson, detail=True)}


@router.post("/{lesson_ref}/complete")
def complete_lesson(
    lesson_ref: str = Path(pattern=r"[0-9a-f-]{36}|[a-z0-9-]{1,100}"),
    user: User = Depends(get_current_user),
    service: EducationService = Depends(get_education_service_dep),
) -> dict[str, Any]:
    """Mark a lesson complete (idempotent; first completion wins)."""
    lesson = _resolve_lesson(lesson_ref, user, service)
    if lesson is None:
        raise AppError("lesson.not_found", "Lesson not found.", status_code=404)
    progress = service.mark_complete(user.id, lesson.id)
    return {
        "data": {
            "lesson_id": str(progress.lesson_id),
            "completed_at": progress.completed_at.isoformat(),
        }
    }
