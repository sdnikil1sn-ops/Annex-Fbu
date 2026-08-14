"""Educator domain — classes, membership, and lesson assignments (Phase 17).

Persisted into ``classes`` / ``class_members`` / ``assignments``. A class
is owned by one user who becomes its 'teacher' member; students join with
the invite code. Assignments link a published lesson (Phase 15) to a
class, and progress is derived by joining members against
``lesson_progress`` — the aggregate below carries the caller's membership
role so the API can render owner-only actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# Membership roles within a class (independent of the global user role).
TEACHER = "teacher"
STUDENT = "student"
MEMBERSHIP_ROLES = (TEACHER, STUDENT)

# Invite codes are 8 uppercase alphanumeric characters (schema CHECK).
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no confusing chars
INVITE_CODE_LENGTH = 8


@dataclass(frozen=True)
class ClassMember:
    """One membership row: a user with a role inside a class."""

    user_id: UUID
    role: str = STUDENT
    class_id: UUID | None = None
    display_name: str | None = None
    joined_at: datetime | None = None


@dataclass(frozen=True)
class Assignment:
    """A lesson assigned to a class, with completion statistics.

    ``completed_count`` / ``member_count`` are populated by progress reads
    so teachers get at-a-glance completion without a second query.
    """

    id: UUID
    class_id: UUID
    lesson_id: UUID
    lesson_slug: str
    lesson_title: str
    assigned_by: UUID
    due_at: datetime | None = None
    created_at: datetime | None = None
    completed_count: int = 0
    member_count: int = 0


@dataclass(frozen=True)
class StudentProgress:
    """One student's completion state for one assignment."""

    user_id: UUID
    display_name: str | None = None
    completed: bool = False
    completed_at: datetime | None = None


@dataclass(frozen=True)
class AssignmentProgress:
    """An assignment with per-student completion, for teachers."""

    assignment: Assignment
    students: tuple[StudentProgress, ...] = ()


@dataclass(frozen=True)
class ClassRoom:
    """A class aggregate with the caller's membership attached.

    Attributes:
        id: Primary key of the ``classes`` row.
        owner_id: The user who created the class.
        name: Display name.
        description: Free-form description.
        invite_code: Short code students use to join.
        created_at: When the class was created.
        role: The caller's membership role (``teacher`` | ``student``),
            or None when the caller is not a member.
        members: Class members (teachers + students), when fetched.
        assignments: Assigned lessons with completion stats, when fetched.
    """

    id: UUID
    owner_id: UUID
    name: str
    description: str
    invite_code: str
    created_at: datetime
    role: str | None = None
    members: tuple[ClassMember, ...] = ()
    assignments: tuple[Assignment, ...] = ()
