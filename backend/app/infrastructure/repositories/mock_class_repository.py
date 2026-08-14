"""In-memory ClassRepository for unit tests (explicit mock per CONTRIBUTING.md)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.ports.repositories import ClassRepository
from app.domain.classroom import (
    STUDENT,
    TEACHER,
    Assignment,
    AssignmentProgress,
    ClassMember,
    ClassRoom,
    StudentProgress,
)


class MockClassRepository(ClassRepository):
    """A deterministic in-memory store implementing the class port.

    Mirrors the PostgreSQL shape: classes with the owner inserted as a
    ``teacher`` member, joinable by invite code, assignments unique per
    (class, lesson), and progress derived from a per-user lesson-completion
    store (the same shape as ``lesson_progress``).
    """

    def __init__(self) -> None:
        self._classes: dict[UUID, ClassRoom] = {}
        self._members: dict[tuple[UUID, UUID], ClassMember] = {}
        self._assignments: dict[UUID, Assignment] = {}
        self._completions: dict[tuple[UUID, UUID], datetime] = {}
        self._lessons: dict[str, UUID] = {}
        self._lesson_titles: dict[UUID, tuple[str, str]] = {}

    # --- seeding helpers for tests ---------------------------------------

    def seed_class(
        self, owner_id: UUID, name: str, *, invite_code: str, description: str = ""
    ) -> ClassRoom:
        """Pre-populate a class with the owner's teacher membership."""
        now = datetime.now(UTC)
        class_id = uuid4()
        room = ClassRoom(
            id=class_id,
            owner_id=owner_id,
            name=name,
            description=description,
            invite_code=invite_code,
            created_at=now,
            role=TEACHER,
        )
        self._classes[class_id] = room
        self._members[(class_id, owner_id)] = ClassMember(
            user_id=owner_id, role=TEACHER, class_id=class_id, joined_at=now
        )
        return room

    def seed_member(self, class_id: UUID, user_id: UUID, *, role: str = STUDENT) -> None:
        """Add a member to a class."""
        self._members[(class_id, user_id)] = ClassMember(
            user_id=user_id,
            role=role,
            class_id=class_id,
            joined_at=datetime.now(UTC),
        )

    def seed_completion(self, user_id: UUID, lesson_id: UUID) -> None:
        """Record a lesson completion (mirrors lesson_progress)."""
        self._completions.setdefault((user_id, lesson_id), datetime.now(UTC))

    def seed_lesson(self, lesson_id: UUID, slug: str, title: str) -> None:
        """Register a published lesson the repository can resolve."""
        self._lessons[slug] = lesson_id
        self._lesson_titles[lesson_id] = (slug, title)

    # --- port implementation ---------------------------------------------

    def create_class(
        self,
        owner_id: UUID,
        name: str,
        description: str,
        invite_code: str,
    ) -> ClassRoom:
        room = ClassRoom(
            id=uuid4(),
            owner_id=owner_id,
            name=name,
            description=description,
            invite_code=invite_code,
            created_at=datetime.now(UTC),
            role=TEACHER,
        )
        self._classes[room.id] = room
        self._members[(room.id, owner_id)] = ClassMember(
            user_id=owner_id,
            role=TEACHER,
            class_id=room.id,
            joined_at=room.created_at,
        )
        return room

    def list_classes(self, user_id: UUID) -> list[ClassRoom]:
        rooms = [
            self._classes[class_id]
            for (class_id, member_id), member in self._members.items()
            if member_id == user_id and class_id in self._classes
        ]
        return sorted(rooms, key=lambda room: room.created_at, reverse=True)

    def get_class(self, class_id: UUID, user_id: UUID) -> ClassRoom | None:
        room = self._classes.get(class_id)
        if room is None:
            return None
        members = [
            member
            for (cid, _uid), member in sorted(self._members.items())
            if cid == class_id
        ]
        return ClassRoom(
            id=room.id,
            owner_id=room.owner_id,
            name=room.name,
            description=room.description,
            invite_code=room.invite_code,
            created_at=room.created_at,
            role=self.membership_role(class_id, user_id),
            members=tuple(members),
        )

    def membership_role(self, class_id: UUID, user_id: UUID) -> str | None:
        member = self._members.get((class_id, user_id))
        return member.role if member else None

    def join_class(self, invite_code: str, user_id: UUID) -> ClassMember | None:
        room = next(
            (room for room in self._classes.values() if room.invite_code == invite_code),
            None,
        )
        if room is None:
            return None
        existing = self._members.get((room.id, user_id))
        if existing is not None:
            return existing
        member = ClassMember(
            user_id=user_id,
            role=STUDENT,
            class_id=room.id,
            joined_at=datetime.now(UTC),
        )
        self._members[(room.id, user_id)] = member
        return member

    def resolve_lesson(self, lesson_ref: str) -> UUID | None:
        try:
            lesson_id = UUID(lesson_ref)
        except ValueError:
            return self._lessons.get(lesson_ref)
        if lesson_id in self._lesson_titles:
            return lesson_id
        return None

    def assign_lesson(
        self,
        class_id: UUID,
        lesson_id: UUID,
        assigned_by: UUID,
        due_at: datetime | None,
    ) -> Assignment | None:
        if class_id not in self._classes:
            return None
        for assignment in self._assignments.values():
            if assignment.class_id == class_id and assignment.lesson_id == lesson_id:
                return assignment
        slug, title = self._lesson_titles.get(lesson_id, ("lesson", "Lesson"))
        assignment = Assignment(
            id=uuid4(),
            class_id=class_id,
            lesson_id=lesson_id,
            lesson_slug=slug,
            lesson_title=title,
            assigned_by=assigned_by,
            due_at=due_at,
            created_at=datetime.now(UTC),
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def list_assignments(self, class_id: UUID) -> list[Assignment]:
        assignments = [
            assignment
            for assignment in self._assignments.values()
            if assignment.class_id == class_id
        ]
        return [
            self._with_stats(assignment)
            for assignment in sorted(
                assignments,
                key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
            )
        ]

    def get_assignment(self, class_id: UUID, assignment_id: UUID) -> Assignment | None:
        assignment = self._assignments.get(assignment_id)
        if assignment is None or assignment.class_id != class_id:
            return None
        return self._with_stats(assignment)

    def delete_assignment(self, class_id: UUID, assignment_id: UUID) -> bool:
        assignment = self._assignments.get(assignment_id)
        if assignment is None or assignment.class_id != class_id:
            return False
        del self._assignments[assignment_id]
        return True

    def assignment_progress(
        self, class_id: UUID, assignment_id: UUID
    ) -> AssignmentProgress | None:
        assignment = self.get_assignment(class_id, assignment_id)
        if assignment is None:
            return None
        students = [
            member
            for (cid, _uid), member in self._members.items()
            if cid == class_id and member.role == STUDENT
        ]
        students.sort(key=lambda member: member.joined_at or datetime.min.replace(tzinfo=UTC))
        return AssignmentProgress(
            assignment=assignment,
            students=tuple(
                StudentProgress(
                    user_id=member.user_id,
                    display_name=member.display_name,
                    completed=(member.user_id, assignment.lesson_id) in self._completions,
                    completed_at=self._completions.get(
                        (member.user_id, assignment.lesson_id)
                    ),
                )
                for member in students
            ),
        )

    def class_progress(self, class_id: UUID) -> list[AssignmentProgress]:
        return [
            progress
            for assignment in self.list_assignments(class_id)
            if (progress := self.assignment_progress(class_id, assignment.id)) is not None
        ]

    def remove_member(self, class_id: UUID, member_id: UUID) -> bool:
        member = self._members.get((class_id, member_id))
        if member is None or member.role == TEACHER:
            return False
        del self._members[(class_id, member_id)]
        return True

    def delete_class(self, class_id: UUID) -> bool:
        if class_id not in self._classes:
            return False
        del self._classes[class_id]
        self._members = {
            key: member
            for key, member in self._members.items()
            if key[0] != class_id
        }
        self._assignments = {
            key: assignment
            for key, assignment in self._assignments.items()
            if assignment.class_id != class_id
        }
        return True

    # --- internals -------------------------------------------------------

    def _with_stats(self, assignment: Assignment) -> Assignment:
        member_count = sum(
            1
            for (cid, _uid), member in self._members.items()
            if cid == assignment.class_id and member.role == STUDENT
        )
        completed_count = sum(
            1
            for (cid, user_id), member in self._members.items()
            if cid == assignment.class_id
            and member.role == STUDENT
            and (user_id, assignment.lesson_id) in self._completions
        )
        return Assignment(
            id=assignment.id,
            class_id=assignment.class_id,
            lesson_id=assignment.lesson_id,
            lesson_slug=assignment.lesson_slug,
            lesson_title=assignment.lesson_title,
            assigned_by=assignment.assigned_by,
            due_at=assignment.due_at,
            created_at=assignment.created_at,
            completed_count=completed_count,
            member_count=member_count,
        )
