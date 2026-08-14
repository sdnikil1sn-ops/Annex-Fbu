"""PostgreSQL implementation of the ClassRepository port (Phase 17).

Classes, membership, and assignments live in their own tables; progress
reports join members against ``lesson_progress`` (Phase 15) so completion
is always derived from the curriculum's single source of truth. The owner
is inserted into ``class_members`` with role ``teacher`` at creation, so
``membership_role`` is the one authorization check the service needs.
Every query is parameterized; identifiers are never built from input.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

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

# Assignment rows joined with the lesson's stable slug and the English
# title (the fallback root) so teachers read friendly names regardless of
# their own locale.
_ASSIGNMENT_SELECT = """
    select a.id, a.class_id, a.lesson_id, a.assigned_by, a.due_at, a.created_at,
           l.slug as lesson_slug,
           coalesce(lc.title, l.slug) as lesson_title,
           (select count(*) from public.class_members m
            where m.class_id = a.class_id and m.role = 'student') as member_count,
           (select count(*) from public.lesson_progress p
            join public.class_members m on m.user_id = p.user_id
                and m.class_id = a.class_id and m.role = 'student'
            where p.lesson_id = a.lesson_id) as completed_count
    from public.assignments a
    join public.lessons l on l.id = a.lesson_id
    left join public.lesson_contents lc on lc.lesson_id = l.id
    left join public.i18n_locales loc on loc.id = lc.locale_id and loc.code = 'en'
"""


def _assignment_from_row(row: dict[str, Any]) -> Assignment:
    return Assignment(
        id=row["id"],
        class_id=row["class_id"],
        lesson_id=row["lesson_id"],
        lesson_slug=row["lesson_slug"],
        lesson_title=row["lesson_title"],
        assigned_by=row["assigned_by"],
        due_at=row["due_at"],
        created_at=row["created_at"],
        completed_count=row["completed_count"] or 0,
        member_count=row["member_count"] or 0,
    )


class PostgresClassRepository(ClassRepository):
    """ClassRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (service role bypasses RLS).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def create_class(
        self,
        owner_id: UUID,
        name: str,
        description: str,
        invite_code: str,
    ) -> ClassRoom:
        """Insert the class and the owner's teacher membership atomically."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                insert into public.classes (owner_id, name, description, invite_code)
                values (%s, %s, %s, %s)
                returning id, owner_id, name, description, invite_code, created_at
                """,
                (owner_id, name, description, invite_code),
            ).fetchone()
            assert row is not None
            conn.execute(
                """
                insert into public.class_members (class_id, user_id, role)
                values (%s, %s, %s)
                """,
                (row["id"], owner_id, TEACHER),
            )
        return ClassRoom(
            id=row["id"],
            owner_id=row["owner_id"],
            name=row["name"],
            description=row["description"],
            invite_code=row["invite_code"],
            created_at=row["created_at"],
            role=TEACHER,
        )

    def list_classes(self, user_id: UUID) -> list[ClassRoom]:
        """Return every class the user owns or belongs to, with their role."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select c.id, c.owner_id, c.name, c.description, c.invite_code,
                       c.created_at, m.role
                from public.classes c
                join public.class_members m
                    on m.class_id = c.id and m.user_id = %s
                order by c.created_at desc, c.id
                """,
                (user_id,),
            ).fetchall()
        return [
            ClassRoom(
                id=row["id"],
                owner_id=row["owner_id"],
                name=row["name"],
                description=row["description"],
                invite_code=row["invite_code"],
                created_at=row["created_at"],
                role=row["role"],
            )
            for row in rows
        ]

    def get_class(self, class_id: UUID, user_id: UUID) -> ClassRoom | None:
        """Fetch a class with the caller's role and the member roster."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                select c.id, c.owner_id, c.name, c.description, c.invite_code,
                       c.created_at, m.role
                from public.classes c
                left join public.class_members m
                    on m.class_id = c.id and m.user_id = %s
                where c.id = %s
                """,
                (user_id, class_id),
            ).fetchone()
            if row is None:
                return None
            members: list[dict[str, Any]] = conn.execute(
                """
                select m.user_id, m.role, m.joined_at, u.display_name
                from public.class_members m
                left join public.users u on u.id = m.user_id
                where m.class_id = %s
                order by m.joined_at, m.user_id
                """,
                (class_id,),
            ).fetchall()
        return ClassRoom(
            id=row["id"],
            owner_id=row["owner_id"],
            name=row["name"],
            description=row["description"],
            invite_code=row["invite_code"],
            created_at=row["created_at"],
            role=row["role"],
            members=tuple(
                ClassMember(
                    user_id=member["user_id"],
                    role=member["role"],
                    class_id=class_id,
                    display_name=member["display_name"],
                    joined_at=member["joined_at"],
                )
                for member in members
            ),
        )

    def membership_role(self, class_id: UUID, user_id: UUID) -> str | None:
        """Return the caller's role in the class, or None when not a member."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                select role from public.class_members
                where class_id = %s and user_id = %s
                """,
                (class_id, user_id),
            ).fetchone()
        return row["role"] if row else None

    def join_class(self, invite_code: str, user_id: UUID) -> ClassMember | None:
        """Join a class by invite code; idempotent, keeps an existing role."""
        with self._connect() as conn:
            class_row: dict[str, Any] | None = conn.execute(
                "select id from public.classes where invite_code = %s",
                (invite_code,),
            ).fetchone()
            if class_row is None:
                return None
            class_id = class_row["id"]
            conn.execute(
                """
                insert into public.class_members (class_id, user_id, role)
                values (%s, %s, %s)
                on conflict (class_id, user_id) do nothing
                """,
                (class_id, user_id, STUDENT),
            )
            row: dict[str, Any] | None = conn.execute(
                """
                select m.user_id, m.role, m.joined_at, u.display_name
                from public.class_members m
                left join public.users u on u.id = m.user_id
                where m.class_id = %s and m.user_id = %s
                """,
                (class_id, user_id),
            ).fetchone()
        assert row is not None
        return ClassMember(
            user_id=row["user_id"],
            role=row["role"],
            class_id=class_id,
            display_name=row["display_name"],
            joined_at=row["joined_at"],
        )

    def resolve_lesson(self, lesson_ref: str) -> UUID | None:
        """Resolve a lesson UUID or stable slug to its id (published only)."""
        with self._connect() as conn:
            if _is_uuid(lesson_ref):
                row: dict[str, Any] | None = conn.execute(
                    """
                    select id from public.lessons
                    where id = %s and published = true
                    """,
                    (lesson_ref,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    select id from public.lessons
                    where slug = %s and published = true
                    """,
                    (lesson_ref,),
                ).fetchone()
        return row["id"] if row else None

    def assign_lesson(
        self,
        class_id: UUID,
        lesson_id: UUID,
        assigned_by: UUID,
        due_at: datetime | None,
    ) -> Assignment | None:
        """Create an assignment; re-assigning a lesson is idempotent.

        ``on conflict ... do update`` with a no-op target returns the
        existing row so repeat calls never duplicate assignments.
        """
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                insert into public.assignments (class_id, lesson_id, assigned_by, due_at)
                values (%s, %s, %s, %s)
                on conflict (class_id, lesson_id) do update
                    set lesson_id = excluded.lesson_id
                returning id, class_id, lesson_id, assigned_by, due_at, created_at
                """,
                (class_id, lesson_id, assigned_by, due_at),
            ).fetchone()
            if row is None:
                return None
            lesson: dict[str, Any] | None = conn.execute(
                """
                select l.slug, coalesce(lc.title, l.slug) as title
                from public.lessons l
                left join public.lesson_contents lc on lc.lesson_id = l.id
                left join public.i18n_locales loc
                    on loc.id = lc.locale_id and loc.code = 'en'
                where l.id = %s
                """,
                (lesson_id,),
            ).fetchone()
        assert lesson is not None
        return Assignment(
            id=row["id"],
            class_id=row["class_id"],
            lesson_id=row["lesson_id"],
            lesson_slug=lesson["slug"],
            lesson_title=lesson["title"],
            assigned_by=row["assigned_by"],
            due_at=row["due_at"],
            created_at=row["created_at"],
        )

    def list_assignments(self, class_id: UUID) -> list[Assignment]:
        """Return a class's assignments with completion statistics."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                f"{_ASSIGNMENT_SELECT} where a.class_id = %s order by a.created_at",
                (class_id,),
            ).fetchall()
        return [_assignment_from_row(row) for row in rows]

    def get_assignment(
        self, class_id: UUID, assignment_id: UUID
    ) -> Assignment | None:
        """Fetch one assignment belonging to a class."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                f"{_ASSIGNMENT_SELECT} where a.class_id = %s and a.id = %s",
                (class_id, assignment_id),
            ).fetchone()
        return _assignment_from_row(row) if row else None

    def delete_assignment(self, class_id: UUID, assignment_id: UUID) -> bool:
        """Remove an assignment; True when a row was deleted."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                delete from public.assignments
                where class_id = %s and id = %s
                """,
                (class_id, assignment_id),
            )
        return cursor.rowcount > 0

    def assignment_progress(
        self, class_id: UUID, assignment_id: UUID
    ) -> AssignmentProgress | None:
        """Per-student completion for one assignment."""
        assignment = self.get_assignment(class_id, assignment_id)
        if assignment is None:
            return None
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                """
                select m.user_id, u.display_name, p.completed_at
                from public.class_members m
                left join public.users u on u.id = m.user_id
                left join public.lesson_progress p
                    on p.user_id = m.user_id and p.lesson_id = %s
                where m.class_id = %s and m.role = 'student'
                order by u.display_name nulls last, m.user_id
                """,
                (assignment.lesson_id, class_id),
            ).fetchall()
        return AssignmentProgress(
            assignment=assignment,
            students=tuple(
                StudentProgress(
                    user_id=row["user_id"],
                    display_name=row["display_name"],
                    completed=row["completed_at"] is not None,
                    completed_at=row["completed_at"],
                )
                for row in rows
            ),
        )

    def class_progress(self, class_id: UUID) -> list[AssignmentProgress]:
        """Per-assignment progress for every assignment in the class."""
        return [
            progress
            for assignment in self.list_assignments(class_id)
            if (progress := self.assignment_progress(class_id, assignment.id)) is not None
        ]

    def remove_member(self, class_id: UUID, member_id: UUID) -> bool:
        """Remove a student from a class; True when a row was deleted.

        Teachers cannot be removed this way (the owner manages the class).
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                delete from public.class_members
                where class_id = %s and user_id = %s and role = 'student'
                """,
                (class_id, member_id),
            )
        return cursor.rowcount > 0

    def delete_class(self, class_id: UUID) -> bool:
        """Delete the class; members and assignments cascade."""
        with self._connect() as conn:
            cursor = conn.execute(
                "delete from public.classes where id = %s",
                (class_id,),
            )
        return cursor.rowcount > 0


def _is_uuid(value: str) -> bool:
    """True when the string parses as a UUID (used to route lookups)."""
    try:
        UUID(value)
    except ValueError:
        return False
    return True
