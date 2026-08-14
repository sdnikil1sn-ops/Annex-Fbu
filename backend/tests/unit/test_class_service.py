"""Unit tests for the ClassService (Phase 17)."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.application.services.class_service import ClassService
from app.domain.classroom import STUDENT, TEACHER
from app.infrastructure.repositories.mock_class_repository import MockClassRepository


def _service() -> tuple[ClassService, MockClassRepository]:
    repository = MockClassRepository()
    return ClassService(repository), repository


def _lesson(repository: MockClassRepository) -> tuple[UUID, str]:
    """Seed one published lesson; returns (id, slug)."""
    lesson_id = uuid4()
    repository.seed_lesson(lesson_id, "spotting-misinformation", "Spotting Misinformation")
    return lesson_id, "spotting-misinformation"


def test_create_class_makes_caller_the_teacher() -> None:
    """Creating a class assigns the creator as its teacher."""
    service, repository = _service()
    owner = uuid4()
    room = service.create_class(owner, "Media Literacy 101", "Spring cohort")

    assert room.owner_id == owner
    assert room.name == "Media Literacy 101"
    assert len(room.invite_code) == 8
    assert room.invite_code.isupper()
    assert service.get_class(room.id, owner) is not None
    assert service.list_classes(owner) == [room]


def test_invite_codes_are_unique() -> None:
    """Generated invite codes do not collide across classes."""
    service, _ = _service()
    owner = uuid4()
    codes = {
        service.create_class(owner, f"Class {index}", "").invite_code for index in range(50)
    }
    assert len(codes) == 50


def test_join_class_by_invite_is_idempotent() -> None:
    """Joining twice keeps a single student membership."""
    service, repository = _service()
    owner, student = uuid4(), uuid4()
    room = service.create_class(owner, "Media Literacy 101", "")

    first = service.join_class(student, room.invite_code)
    second = service.join_class(student, room.invite_code)

    assert first is not None and first.role == STUDENT
    assert second is not None and second.user_id == student
    assert first.joined_at == second.joined_at

    listed = service.list_classes(student)
    assert [item.id for item in listed] == [room.id]
    fetched = service.get_class(room.id, student)
    assert fetched is not None and fetched.role == STUDENT


def test_join_class_rejects_unknown_invite() -> None:
    """An unknown invite code yields None, not an error."""
    service, _ = _service()
    assert service.join_class(uuid4(), "ZZZZZZZZ") is None


def test_join_class_keeps_teacher_role_for_owner() -> None:
    """The owner joining via their own code keeps the teacher role."""
    service, _ = _service()
    owner = uuid4()
    room = service.create_class(owner, "Media Literacy 101", "")
    member = service.join_class(owner, room.invite_code)
    assert member is not None and member.role == TEACHER


def test_assign_lesson_requires_teacher() -> None:
    """A student cannot assign lessons; a non-member gets None too."""
    service, repository = _service()
    owner, student, outsider = uuid4(), uuid4(), uuid4()
    lesson_id, slug = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")
    service.join_class(student, room.invite_code)

    assert service.resolve_lesson(str(lesson_id)) == lesson_id
    assert service.resolve_lesson(slug) == lesson_id
    assert service.resolve_lesson("no-such-lesson") is None

    assignment = service.assign_lesson(room.id, lesson_id, owner, due_at=None)
    assert assignment is not None
    assert assignment.lesson_slug == slug

    assert service.assign_lesson(room.id, lesson_id, student, None) is None
    assert service.assign_lesson(room.id, lesson_id, outsider, None) is None


def test_assign_lesson_is_idempotent_per_lesson() -> None:
    """Re-assigning the same lesson returns the original assignment."""
    service, repository = _service()
    owner = uuid4()
    lesson_id, _ = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")

    first = service.assign_lesson(room.id, lesson_id, owner, None)
    second = service.assign_lesson(room.id, lesson_id, owner, None)

    assert first is not None and second is not None
    assert first.id == second.id


def test_list_assignments_members_only() -> None:
    """Members see assignments; outsiders get None."""
    service, repository = _service()
    owner, student = uuid4(), uuid4()
    lesson_id, _ = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")
    service.join_class(student, room.invite_code)
    service.assign_lesson(room.id, lesson_id, owner, None)

    for_member = service.list_assignments(room.id, student)
    assert for_member is not None and len(for_member) == 1
    assert service.list_assignments(room.id, uuid4()) is None


def test_class_progress_tracks_student_completion() -> None:
    """Progress reports per-student completion from lesson_progress."""
    service, repository = _service()
    owner, student_a, student_b = uuid4(), uuid4(), uuid4()
    lesson_id, _ = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")
    service.join_class(student_a, room.invite_code)
    service.join_class(student_b, room.invite_code)
    service.assign_lesson(room.id, lesson_id, owner, None)
    repository.seed_completion(student_a, lesson_id)

    progress = service.class_progress(room.id, owner)
    assert progress is not None and len(progress) == 1
    students = progress[0].students
    by_user = {student.user_id: student for student in students}
    assert by_user[student_a].completed is True
    assert by_user[student_b].completed is False
    assert progress[0].assignment.completed_count == 1
    assert progress[0].assignment.member_count == 2

    # Non-teachers cannot read progress.
    assert service.class_progress(room.id, student_a) is None
    assert service.class_progress(room.id, uuid4()) is None


def test_assignment_progress_for_unknown_assignment() -> None:
    """An unknown assignment yields None even for the teacher."""
    service, repository = _service()
    owner = uuid4()
    lesson_id, _ = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")
    assignment = service.assign_lesson(room.id, lesson_id, owner, None)
    assert assignment is not None

    assert service.assignment_progress(room.id, assignment.id, owner) is not None
    assert service.assignment_progress(room.id, uuid4(), owner) is None


def test_remove_member_teacher_only() -> None:
    """Removing a student works for the teacher, not for others."""
    service, _ = _service()
    owner, student, outsider = uuid4(), uuid4(), uuid4()
    room = service.create_class(owner, "Media Literacy 101", "")
    member = service.join_class(student, room.invite_code)
    assert member is not None

    assert service.remove_member(room.id, student, outsider) is None
    assert service.remove_member(room.id, student, owner) is True
    # The student can no longer see the class.
    assert service.get_class(room.id, student) is None


def test_remove_member_missing_member_is_false() -> None:
    """Removing a non-member reports False, not None."""
    service, _ = _service()
    owner = uuid4()
    room = service.create_class(owner, "Media Literacy 101", "")
    assert service.remove_member(room.id, uuid4(), owner) is False


def test_delete_assignment_teacher_only() -> None:
    """Unassigning works for the teacher and hides the class otherwise."""
    service, repository = _service()
    owner, student = uuid4(), uuid4()
    lesson_id, _ = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")
    service.join_class(student, room.invite_code)
    assignment = service.assign_lesson(room.id, lesson_id, owner, None)
    assert assignment is not None

    assert service.delete_assignment(room.id, assignment.id, student) is None
    assert service.delete_assignment(room.id, assignment.id, owner) is True
    assert service.list_assignments(room.id, student) == []


def test_delete_class_owner_only() -> None:
    """Deleting a class removes it and its members for everyone."""
    service, repository = _service()
    owner, student = uuid4(), uuid4()
    lesson_id, _ = _lesson(repository)
    room = service.create_class(owner, "Media Literacy 101", "")
    service.join_class(student, room.invite_code)
    service.assign_lesson(room.id, lesson_id, owner, None)

    assert service.delete_class(room.id, student) is None
    assert service.delete_class(room.id, owner) is True
    assert service.get_class(room.id, owner) is None
    assert service.list_classes(owner) == []
    assert service.list_classes(student) == []


def test_create_class_strips_whitespace() -> None:
    """Names and descriptions are trimmed before persistence."""
    service, _ = _service()
    room = service.create_class(uuid4(), "  Media Literacy 101  ", "   ")
    assert room.name == "Media Literacy 101"
    assert room.description == ""
