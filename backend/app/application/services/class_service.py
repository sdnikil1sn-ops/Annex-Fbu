"""Class service — educator tools (Phase 17).

Coordinates classes, membership, and lesson assignments. Authorization is
enforced here at the service boundary (never only in the UI): teacher-only
operations return None when the caller is not a teacher, which the API
layer turns into a 404 that never reveals whether the class exists.
Assignment progress is derived from ``lesson_progress`` (Phase 15) joined
against members, so teachers track class completion without a separate
progress store.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from uuid import UUID

from app.application.ports.repositories import ClassRepository
from app.domain.classroom import (
    INVITE_CODE_ALPHABET,
    INVITE_CODE_LENGTH,
    TEACHER,
    Assignment,
    AssignmentProgress,
    ClassMember,
    ClassRoom,
)


class ClassService:
    """Coordinates class management, membership, and assignment progress.

    Args:
        repository: The class persistence port (Phase 17).
    """

    def __init__(self, repository: ClassRepository) -> None:
        self._repository = repository

    def create_class(
        self, owner_id: UUID, name: str, description: str
    ) -> ClassRoom:
        """Create a class owned by the caller (who becomes its teacher)."""
        return self._repository.create_class(
            owner_id=owner_id,
            name=name.strip(),
            description=description.strip(),
            invite_code=self._generate_invite_code(),
        )

    def list_classes(self, user_id: UUID) -> list[ClassRoom]:
        """Return every class the user owns or belongs to, with their role."""
        return self._repository.list_classes(user_id)

    def get_class(self, class_id: UUID, user_id: UUID) -> ClassRoom | None:
        """Fetch one class aggregate with the caller's role and members.

        Returns None when the class does not exist or the caller is not a
        member (the API answers 404 either way).
        """
        room = self._repository.get_class(class_id, user_id)
        if room is None or room.role is None:
            return None
        return room

    def join_class(self, user_id: UUID, invite_code: str) -> ClassMember | None:
        """Join a class by its invite code (idempotent).

        Returns None when no class uses that invite code. Re-joining a
        class the user already belongs to returns the existing membership.
        """
        return self._repository.join_class(invite_code.strip().upper(), user_id)

    def resolve_lesson(self, lesson_ref: str) -> UUID | None:
        """Resolve a lesson reference (UUID or slug) to its id.

        Lets the API answer ``lesson.not_found`` distinctly from
        ``class.not_found`` before attempting an assignment.
        """
        return self._repository.resolve_lesson(lesson_ref)

    def assign_lesson(
        self,
        class_id: UUID,
        lesson_id: UUID,
        assigned_by: UUID,
        due_at: datetime | None,
    ) -> Assignment | None:
        """Assign a lesson to a class (teacher only, idempotent per lesson).

        Returns None when the caller is not a teacher of the class;
        re-assigning the same lesson returns the existing assignment.
        """
        if self._repository.membership_role(class_id, assigned_by) != TEACHER:
            return None
        return self._repository.assign_lesson(
            class_id, lesson_id, assigned_by=assigned_by, due_at=due_at
        )

    def list_assignments(
        self, class_id: UUID, user_id: UUID
    ) -> list[Assignment] | None:
        """Return a class's assignments with completion stats (members only)."""
        if self._repository.membership_role(class_id, user_id) is None:
            return None
        return self._repository.list_assignments(class_id)

    def assignment_progress(
        self, class_id: UUID, assignment_id: UUID, user_id: UUID
    ) -> AssignmentProgress | None:
        """Per-student completion for one assignment (teacher only)."""
        if self._repository.membership_role(class_id, user_id) != TEACHER:
            return None
        return self._repository.assignment_progress(class_id, assignment_id)

    def class_progress(
        self, class_id: UUID, user_id: UUID
    ) -> list[AssignmentProgress] | None:
        """Per-assignment, per-student completion for a class (teacher only)."""
        if self._repository.membership_role(class_id, user_id) != TEACHER:
            return None
        return self._repository.class_progress(class_id)

    def remove_member(
        self, class_id: UUID, member_id: UUID, user_id: UUID
    ) -> bool | None:
        """Remove a student from a class (teacher only).

        Returns None when the caller is not a teacher, False when the
        member does not exist, True on removal.
        """
        if self._repository.membership_role(class_id, user_id) != TEACHER:
            return None
        return self._repository.remove_member(class_id, member_id)

    def delete_assignment(
        self, class_id: UUID, assignment_id: UUID, user_id: UUID
    ) -> bool | None:
        """Unassign a lesson (teacher only). None when not a teacher."""
        if self._repository.membership_role(class_id, user_id) != TEACHER:
            return None
        return self._repository.delete_assignment(class_id, assignment_id)

    def delete_class(self, class_id: UUID, user_id: UUID) -> bool | None:
        """Delete a class and its members/assignments (owner only)."""
        if self._repository.membership_role(class_id, user_id) != TEACHER:
            return None
        return self._repository.delete_class(class_id)

    # --- internals -------------------------------------------------------

    @staticmethod
    def _generate_invite_code() -> str:
        """Generate an 8-char invite code from the unambiguous alphabet."""
        return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))
