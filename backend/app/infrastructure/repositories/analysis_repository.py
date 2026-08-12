"""PostgreSQL implementation of the AnalysisRepository port.

Connects directly to the Supabase PostgreSQL endpoint via ``DATABASE_URL``
using psycopg. Every query is parameterized; identifiers are never built
from input. The service role / superuser bypasses RLS for worker writes.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.application.ports.repositories import AnalysisRepository, Cursor
from app.domain.analysis import Analysis, AnalysisInputType, AnalysisStatus

# Columns shared by every query in this repository.
_COLUMNS = (
    "id, user_id, input_type, status, locale, failure_reason, content, report, "
    "created_at, completed_at"
)


def _report_param(report: dict[str, Any] | None) -> Jsonb | None:
    """Adapt a report dict for a jsonb column (SQL NULL when absent).

    psycopg does not adapt plain ``dict`` to ``jsonb`` automatically, so the
    wrapper must be explicit (``psycopg.types.json.Jsonb``).
    """
    return Jsonb(report) if report is not None else None


class PostgresAnalysisRepository(AnalysisRepository):
    """AnalysisRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (e.g. the Supabase local or
            pooled production endpoint).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    @staticmethod
    def _from_row(row: dict[str, Any]) -> Analysis:
        return Analysis(
            analysis_id=row["id"],
            user_id=row["user_id"],
            input_type=AnalysisInputType(row["input_type"]),
            status=AnalysisStatus(row["status"]),
            locale=row["locale"],
            failure_reason=row["failure_reason"],
            content=row["content"],
            report=row["report"],
            created_at=row["created_at"],
            completed_at=row["completed_at"],
        )

    def create(self, analysis: Analysis) -> Analysis:
        """Insert the analysis row and return it."""
        with self._connect() as conn:
            conn.execute(
                f"""
                insert into public.analyses ({_COLUMNS})
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    analysis.analysis_id,
                    analysis.user_id,
                    analysis.input_type.value,
                    analysis.status.value,
                    analysis.locale,
                    analysis.failure_reason,
                    analysis.content,
                    _report_param(analysis.report),
                    analysis.created_at,
                    analysis.completed_at,
                ),
            )
        return analysis

    def get(self, analysis_id: UUID) -> Analysis | None:
        """Fetch one analysis by ID, or None when absent."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                f"select {_COLUMNS} from public.analyses where id = %s",
                (analysis_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_by_user(
        self, user_id: UUID, *, limit: int = 50, cursor: Cursor | None = None
    ) -> list[Analysis]:
        """List a user's analyses newest-first, cursor-paginated.

        The cursor is the ``(created_at, id)`` of the last returned row; the
        row-value comparison keeps pagination stable even when timestamps
        tie (order is ``created_at desc, id desc``).
        """
        with self._connect() as conn:
            if cursor is None:
                rows: list[dict[str, Any]] = conn.execute(
                    f"""
                    select {_COLUMNS} from public.analyses
                    where user_id = %s
                    order by created_at desc, id desc
                    limit %s
                    """,
                    (user_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"""
                    select {_COLUMNS} from public.analyses
                    where user_id = %s and (created_at, id) < (%s, %s)
                    order by created_at desc, id desc
                    limit %s
                    """,
                    (user_id, cursor[0], cursor[1], limit),
                ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_status(self, analysis: Analysis) -> Analysis:
        """Persist the current status/failure/completion of an analysis."""
        with self._connect() as conn:
            conn.execute(
                """
                update public.analyses
                set status = %s, failure_reason = %s, report = %s, completed_at = %s
                where id = %s
                """,
                (
                    analysis.status.value,
                    analysis.failure_reason,
                    _report_param(analysis.report),
                    analysis.completed_at,
                    analysis.analysis_id,
                ),
            )
        return analysis

    def delete(self, analysis_id: UUID) -> bool:
        """Delete an analysis; returns True when a row was removed."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                "delete from public.analyses where id = %s returning id",
                (analysis_id,),
            ).fetchone()
        return row is not None
