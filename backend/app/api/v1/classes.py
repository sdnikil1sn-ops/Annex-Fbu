"""Educator endpoints — v1 contract (Phase 17).

Classes, membership, and lesson assignments: any authenticated user can
create a class (becoming its teacher) and invite others with the invite
code; teachers assign published lessons and read class-wide completion
progress. Authorization is enforced at the service boundary — calls from
non-members/non-teachers answer ``class.not_found`` and never reveal
whether a class exists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_class_service_dep, get_current_user
from app.api.errors import AppError
from app.application.services.class_service import ClassService
from app.domain.classroom import (
    Assignment,
    AssignmentProgress,
    ClassMember,
    ClassRoom,
)
from app.domain.user import User

router = APIRouter(prefix="/classes", tags=["classes"])


class CreateClassRequest(BaseModel):
    """Body for ``POST /classes``."""

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2_000)


class JoinClassRequest(BaseModel):
    """Body for ``POST /classes/{id}/join``."""

    invite_code: str = Field(min_length=8, max_length=8, pattern=r"^[A-Za-z0-9]{8}$")


class AssignLessonRequest(BaseModel):
    """Body for ``POST /classes/{id}/assignments``.

    ``lesson_ref`` accepts either a lesson UUID or its stable slug.
    """

    lesson_ref: str = Field(min_length=1, max_length=120)
    due_at: datetime | None = None


def _member_payload(member: ClassMember) -> dict[str, Any]:
    return {
        "user_id": str(member.user_id),
        "role": member.role,
        "display_name": member.display_name,
        "joined_at": member.joined_at.isoformat() if member.joined_at else None,
    }


def _assignment_payload(assignment: Assignment) -> dict[str, Any]:
    return {
        "id": str(assignment.id),
        "class_id": str(assignment.class_id),
        "lesson_id": str(assignment.lesson_id),
        "lesson_slug": assignment.lesson_slug,
        "lesson_title": assignment.lesson_title,
        "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
        "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
        "completed_count": assignment.completed_count,
        "member_count": assignment.member_count,
    }


def _progress_payload(progress: AssignmentProgress) -> dict[str, Any]:
    return {
        "assignment": _assignment_payload(progress.assignment),
        "students": [
            {
                "user_id": str(student.user_id),
                "display_name": student.display_name,
                "completed": student.completed,
                "completed_at": (
                    student.completed_at.isoformat() if student.completed_at else None
                ),
            }
            for student in progress.students
        ],
    }


def _class_payload(room: ClassRoom, *, detail: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": str(room.id),
        "owner_id": str(room.owner_id),
        "name": room.name,
        "description": room.description,
        "invite_code": room.invite_code,
        "role": room.role,
        "created_at": room.created_at.isoformat(),
    }
    if detail:
        payload["members"] = [_member_payload(member) for member in room.members]
        payload["assignments"] = [
            _assignment_payload(assignment) for assignment in room.assignments
        ]
    return payload


@router.post("", status_code=201)
def create_class(
    body: CreateClassRequest,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Create a class; the caller becomes its teacher."""
    room = service.create_class(user.id, body.name, body.description)
    return {"data": _class_payload(room)}


@router.get("")
def list_classes(
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """List the caller's classes (owned or joined) with their role."""
    rooms = service.list_classes(user.id)
    return {"data": [_class_payload(room) for room in rooms]}


@router.get("/{class_id}")
def get_class(
    class_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Fetch one class with its member roster (members only)."""
    room = service.get_class(class_id, user.id)
    if room is None:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": _class_payload(room, detail=True)}


@router.post("/{class_id}/join")
def join_class(
    class_id: UUID,
    body: JoinClassRequest,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Join a class by its invite code (idempotent).

    The class is resolved from the invite code in the body — the URL id
    is not trusted for joining, so a stale or wrong link cannot
    misdirect a join.
    """
    member = service.join_class(user.id, body.invite_code)
    if member is None or member.class_id != class_id:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": _member_payload(member)}


@router.post("/{class_id}/assignments", status_code=201)
def assign_lesson(
    class_id: UUID,
    body: AssignLessonRequest,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Assign a published lesson to a class (teacher only, idempotent)."""
    lesson_id = service.resolve_lesson(body.lesson_ref)
    if lesson_id is None:
        raise AppError("lesson.not_found", "Lesson not found.", status_code=404)
    assignment = service.assign_lesson(
        class_id, lesson_id, assigned_by=user.id, due_at=body.due_at
    )
    if assignment is None:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": _assignment_payload(assignment)}


@router.get("/{class_id}/assignments")
def list_assignments(
    class_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """List a class's assignments with completion stats (members only)."""
    assignments = service.list_assignments(class_id, user.id)
    if assignments is None:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": [_assignment_payload(assignment) for assignment in assignments]}


@router.get("/{class_id}/progress")
def class_progress(
    class_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Per-assignment, per-student completion for a class (teacher only)."""
    progress = service.class_progress(class_id, user.id)
    if progress is None:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": [_progress_payload(item) for item in progress]}


@router.get("/{class_id}/assignments/{assignment_id}/progress")
def assignment_progress(
    class_id: UUID,
    assignment_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Per-student completion for one assignment (teacher only)."""
    progress = service.assignment_progress(class_id, assignment_id, user.id)
    if progress is None:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": _progress_payload(progress)}


@router.delete("/{class_id}/assignments/{assignment_id}")
def unassign_lesson(
    class_id: UUID,
    assignment_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Remove an assignment (teacher only)."""
    deleted = service.delete_assignment(class_id, assignment_id, user.id)
    if not deleted:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": {"deleted": str(assignment_id)}}


@router.delete("/{class_id}/members/{member_id}")
def remove_member(
    class_id: UUID,
    member_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Remove a student from a class (teacher only)."""
    removed = service.remove_member(class_id, member_id, user.id)
    if not removed:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": {"removed": str(member_id)}}


@router.delete("/{class_id}")
def delete_class(
    class_id: UUID,
    user: User = Depends(get_current_user),
    service: ClassService = Depends(get_class_service_dep),
) -> dict[str, Any]:
    """Delete a class and its members/assignments (owner only)."""
    deleted = service.delete_class(class_id, user.id)
    if not deleted:
        raise AppError("class.not_found", "Class not found.", status_code=404)
    return {"data": {"deleted": str(class_id)}}
