"""PostgreSQL implementation of the SourceRepository port (Phase 14).

Sources and their latest credibility score are read together via a lateral
join so the aggregate is assembled in one query. Phase 19 attaches the
community credibility signal: an aggregated count + average from
``source_feedback`` and (optionally) the caller's own rating. Every query
is parameterized; identifiers are never built from input.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.application.ports.repositories import SourceRepository
from app.domain.source import Source, SourceFeedback

# Source row + the latest score (lateral join keeps the aggregate atomic)
# + the community feedback aggregate and the caller's own rating, when a
# user id is supplied. The feedback subqueries count/avg every rating and
# read the caller's row for ``my_rating``.
_SOURCE_SELECT = """
    select s.id, s.domain, s.name, s.country, s.language, s.category,
           ss.score, ss.signals, ss.model, ss.computed_at,
           fb.count as feedback_count, fb.average as feedback_average,
           mine.rating as my_rating
    from public.sources s
    left join lateral (
        select score, signals, model, computed_at
        from public.source_scores
        where source_id = s.id
        order by computed_at desc
        limit 1
    ) ss on true
    left join lateral (
        select count(*) as count, round(avg(rating), 2) as average
        from public.source_feedback
        where source_id = s.id
    ) fb on true
    left join lateral (
        select rating
        from public.source_feedback
        where source_id = s.id and user_id = %s
        limit 1
    ) mine on true
"""


def _from_row(row: dict[str, Any]) -> Source:
    feedback = SourceFeedback(
        count=row["feedback_count"] or 0,
        average=float(row["feedback_average"]) if row["feedback_average"] is not None else None,
        my_rating=row["my_rating"],
    )
    return Source(
        id=row["id"],
        domain=row["domain"],
        name=row["name"],
        country=row["country"],
        language=row["language"],
        category=row["category"],
        score=float(row["score"]) if row["score"] is not None else None,
        signals=row["signals"],
        model=row["model"],
        computed_at=row["computed_at"],
        community=feedback,
    )


class PostgresSourceRepository(SourceRepository):
    """SourceRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (service role bypasses RLS).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def get_by_domain(
        self, domain: str, *, user_id: UUID | None = None
    ) -> Source | None:
        """Fetch one source profile with its latest credibility score."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                f"{_SOURCE_SELECT} where s.domain = %s",
                (user_id, domain),
            ).fetchone()
        return _from_row(row) if row else None

    def search(
        self, query: str, *, limit: int = 20, user_id: UUID | None = None
    ) -> list[Source]:
        """Search by domain or name (case-insensitive substring)."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                f"""
                {_SOURCE_SELECT}
                where s.domain ilike %s or s.name ilike %s
                order by s.domain
                limit %s
                """,
                (user_id, f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [_from_row(row) for row in rows]

    def rate(self, domain: str, user_id: UUID, rating: int) -> Source | None:
        """Record one user's credibility rating (1–5), upserting per user.

        Returns the updated profile with the community aggregate, or None
        when the source does not exist.
        """
        with self._connect() as conn:
            source_row: dict[str, Any] | None = conn.execute(
                "select id from public.sources where domain = %s",
                (domain,),
            ).fetchone()
            if source_row is None:
                return None
            conn.execute(
                """
                insert into public.source_feedback (source_id, user_id, rating)
                values (%s, %s, %s)
                on conflict (source_id, user_id)
                do update set rating = excluded.rating
                """,
                (source_row["id"], user_id, rating),
            )
        return self.get_by_domain(domain, user_id=user_id)
