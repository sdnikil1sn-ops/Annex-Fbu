"""Integration tests: PostgresClassRepository against a real database.

Classes/members/assignments are created by migration 20260813000001,
which is applied by helpers.apply_migrations on every run. Lessons are
seeded by 20260812000006, so assignment resolution works out of the box.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from app.application.ports.repositories import ClassRepository
from app.infrastructure.repositories.class_repository import PostgresClassRepository

from tests.integration.helpers import apply_migrations, create_user

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> ClassRepository:
    """A fresh-schema Postgres class repository per test (seeded)."""
    apply_migrations(TEST_DSN)
    return PostgresClassRepository(TEST_DSN)


def test_create_class_creates_teacher_membership(repository: ClassRepository) -> None:
    """Creating a class inserts the owner as a teacher member."""
    owner = uuid4()
    create_user(TEST_DSN, owner)
    room = repository.create_class(owner, "Media Literacy 101", "Spring", "ABCD1234")

    assert room.owner_id == owner
    assert room.role == "teacher"
    assert repository.membership_role(room.id, owner) == "teacher"
    assert [item.id for item in repository.list_classes(owner)] == [room.id]


def test_join_class_by_invite_code(repository: ClassRepository) -> None:
    """A student joins with the invite code; re-join is idempotent."""
    owner, student = uuid4(), uuid4()
    create_user(TEST_DSN, owner)
    create_user(TEST_DSN, student)
    room = repository.create_class(owner, "Media Literacy 101", "", "ABCD1234")

    member = repository.join_class("ABCD1234", student)
    assert member is not None and member.role == "student"
    assert member.class_id == room.id

    again = repository.join_class("abcd1234", student)  # case-insensitive
    assert again is not None and again.joined_at == member.joined_at

    fetched = repository.get_class(room.id, student)
    assert fetched is not None
    assert fetched.role == "student"
    assert {m.user_id for m in fetched.members} == {owner, student}


def test_join_class_unknown_code_is_none(repository: ClassRepository) -> None:
    """An unknown invite code returns None, not an error."""
    assert repository.join_class("ZZZZZZZZ", uuid4()) is None


def test_assign_lesson_and_progress(repository: ClassRepository) -> None:
    """Assignments resolve published lessons and track completion."""
    owner, student = uuid4(), uuid4()
    create_user(TEST_DSN, owner)
    create_user(TEST_DSN, student)
    room = repository.create_class(owner, "Media Literacy 101", "", "ABCD1234")
    repository.join_class("ABCD1234", student)

    # Resolve the seeded lesson by slug and by id.
    lesson_id = repository.resolve_lesson("spotting-misinformation")
    assert lesson_id is not None
    assert repository.resolve_lesson(str(lesson_id)) == lesson_id
    assert repository.resolve_lesson("no-such-lesson") is None

    assignment = repository.assign_lesson(room.id, lesson_id, owner, due_at=None)
    assert assignment is not None
    assert assignment.lesson_slug == "spotting-misinformation"

    # Re-assigning the same lesson is idempotent.
    again = repository.assign_lesson(room.id, lesson_id, owner, due_at=None)
    assert again is not None and again.id == assignment.id

    listed = repository.list_assignments(room.id)
    assert len(listed) == 1
    assert listed[0].member_count == 1
    assert listed[0].completed_count == 0

    # Mark the lesson complete through lesson_progress (Phase 15 path).
    mark_lesson_complete(TEST_DSN, student, lesson_id)
    progress = repository.assignment_progress(room.id, assignment.id)
    assert progress is not None
    students = {item.user_id: item for item in progress.students}
    assert students[student].completed is True
    assert students[student].completed_at is not None

    class_progress = repository.class_progress(room.id)
    assert len(class_progress) == 1
    assert class_progress[0].assignment.completed_count == 1


def test_remove_member_and_assignments(repository: ClassRepository) -> None:
    """Removing a student drops them from progress; unassigning works."""
    owner, student = uuid4(), uuid4()
    create_user(TEST_DSN, owner)
    create_user(TEST_DSN, student)
    room = repository.create_class(owner, "Media Literacy 101", "", "ABCD1234")
    repository.join_class("ABCD1234", student)
    lesson_id = repository.resolve_lesson("verifying-images")
    assert lesson_id is not None
    assignment = repository.assign_lesson(room.id, lesson_id, owner, due_at=None)
    assert assignment is not None

    assert repository.remove_member(room.id, student) is True
    assert repository.remove_member(room.id, student) is False

    progress = repository.assignment_progress(room.id, assignment.id)
    assert progress is not None and progress.students == ()

    assert repository.delete_assignment(room.id, assignment.id) is True
    assert repository.list_assignments(room.id) == []


def test_delete_class_cascades(repository: ClassRepository) -> None:
    """Deleting a class removes members and assignments."""
    owner, student = uuid4(), uuid4()
    create_user(TEST_DSN, owner)
    create_user(TEST_DSN, student)
    room = repository.create_class(owner, "Media Literacy 101", "", "ABCD1234")
    repository.join_class("ABCD1234", student)
    lesson_id = repository.resolve_lesson("analyzing-claims")
    assert lesson_id is not None
    repository.assign_lesson(room.id, lesson_id, owner, due_at=None)

    assert repository.delete_class(room.id) is True
    assert repository.list_classes(owner) == []
    assert repository.list_assignments(room.id) == []
    assert repository.get_class(room.id, owner) is None


def mark_lesson_complete(dsn: str, user_id, lesson_id) -> None:
    """Insert a lesson_progress row directly (the Phase 15 completion path)."""
    import psycopg

    with psycopg.connect(dsn) as conn:
        conn.execute(
            """
            insert into public.lesson_progress (user_id, lesson_id)
            values (%s, %s)
            on conflict (user_id, lesson_id) do nothing
            """,
            (user_id, lesson_id),
        )
