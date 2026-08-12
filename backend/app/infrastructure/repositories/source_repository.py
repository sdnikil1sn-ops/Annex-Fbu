"""PostgreSQL implementation of the SourceRepository port (Phase 14).

Sources and their latest credibility score are read together via a lateral
join so the aggregate is assembled in one query. Every query is
parameterized; identifiers are never built from input.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.application.ports.repositories import SourceRepository
from app.domain.source import Source

# Source row + the latest score (lateral join keeps the aggregate atomic).
_SOURCE_SELECT = """
    select s.id, s.domain, s.name, s.country, s.language, s.category,
           ss.score, ss.signals, ss.model, ss.computed_at
    from public.sources s
    left join lateral (
        select score, signals, model, computed_at
        from public.source_scores
        where source_id = s.id
        order by computed_at desc
        limit 1
    ) ss on true
"""


def _from_row(row: dict[str, Any]) -> Source:
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

    def get_by_domain(self, domain: str) -> Source | None:
        """Fetch one source profile with its latest credibility score."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                f"{_SOURCE_SELECT} where s.domain = %s",
                (domain,),
            ).fetchone()
        return _from_row(row) if row else None

    def search(self, query: str, *, limit: int = 20) -> list[Source]:
        """Search by domain or name (case-insensitive substring)."""
        with self._connect() as conn:
            rows: list[dict[str, Any]] = conn.execute(
                f"""
                {_SOURCE_SELECT}
                where s.domain ilike %s or s.name ilike %s
                order by s.domain
                limit %s
                """,
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [_from_row(row) for row in rows]
