"""PostgreSQL implementation of the LessonRepository port (Phase 15).

Lessons, their content (resolved to the best available locale in the
caller's fallback chain), and the caller's progress are read together in
one query so the aggregate is atomic. Content resolution uses a lateral
join ordered by ``array_position`` over the chain — the requested locale
wins, falling back toward the default. Every query is parameterized;
identifiers are never built from input.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.application.ports.repositories import LessonRepository
from app.domain.lesson import Lesson, LessonContent, LessonProgress, sections_from_json

# Lessons + best-chain-locale content + caller progress. The chain is a
# Postgres text array ordered requested → parent → … → default; the lateral
# join picks the content row whose locale appears earliest in it.
_LESSON_SELECT = """
    select l.id, l.slug, l.difficulty, l.category, l.estimated_minutes,
           l.order_index, l.published,
           c.locale_code, c.title, c.summary, c.sections,
           p.completed_at
    from public.lessons l
    left join lateral (
        select loc.code as locale_code, lc.title, lc.summary, lc.sections
        from public.lesson_contents lc
        join public.i18n_locales loc on loc.id = lc.locale_id
        where lc.lesson_id = l.id and loc.code = any(%s)
        order by array_position(%s, loc.code)
        limit 1
    ) c on true
    left join public.lesson_progress p
        on p.lesson_id = l.id and p.user_id = %s
"""


def _from_row(row: dict[str, Any]) -> Lesson:
    content: LessonContent | None = None
    if row.get("locale_code") is not None:
        content = LessonContent(
            locale_code=row["locale_code"],
            title=row["title"],
            summary=row["summary"],
            sections=sections_from_json(row["sections"] or []),
        )
    return Lesson(
        id=row["id"],
        slug=row["slug"],
        difficulty=row["difficulty"],
        category=row["category"],
        estimated_minutes=row["estimated_minutes"],
        order_index=row["order_index"],
        published=row["published"],
        content=content,
        completed=row["completed_at"] is not None,
        completed_at=row["completed_at"],
    )


class PostgresLessonRepository(LessonRepository):
    """LessonRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (service role bypasses RLS).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def list_lessons(
        self, *, chain: list[str], user_id: UUID | None = None
    ) -> list[Lesson]:
        """Return published lessons ordered by the curriculum position."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                f"""
                {_LESSON_SELECT}
                where l.published = true
                order by l.order_index, l.created_at
                """,
                (chain, chain, user_id),
            ).fetchall()
        return [_from_row(row) for row in rows]

    def get_lesson(
        self, lesson_id: UUID, *, chain: list[str], user_id: UUID | None = None
    ) -> Lesson | None:
        """Fetch one published lesson by id."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                f"""
                {_LESSON_SELECT}
                where l.published = true and l.id = %s
                """,
                (chain, chain, user_id, lesson_id),
            ).fetchone()
        return _from_row(row) if row else None

    def get_by_slug(
        self, slug: str, *, chain: list[str], user_id: UUID | None = None
    ) -> Lesson | None:
        """Fetch one published lesson by its stable slug."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                f"""
                {_LESSON_SELECT}
                where l.published = true and l.slug = %s
                """,
                (chain, chain, user_id, slug),
            ).fetchone()
        return _from_row(row) if row else None

    def mark_complete(self, user_id: UUID, lesson_id: UUID) -> LessonProgress:
        """Record a completion idempotently; return the stored timestamp.

        ``on conflict do nothing`` keeps the first completion time — a
        re-completion never overwrites the original.
        """
        with self._connect() as conn:
            conn.execute(
                """
                insert into public.lesson_progress (user_id, lesson_id)
                values (%s, %s)
                on conflict (user_id, lesson_id) do nothing
                """,
                (user_id, lesson_id),
            )
            row: dict[str, Any] | None = conn.execute(
                """
                select completed_at
                from public.lesson_progress
                where user_id = %s and lesson_id = %s
                """,
                (user_id, lesson_id),
            ).fetchone()
        assert row is not None  # The insert above guarantees the row exists.
        return LessonProgress(lesson_id=lesson_id, completed_at=row["completed_at"])
