"""PostgreSQL implementation of the ClaimRepository port (Phase 14).

Persists the claim row, its verdict row, and its evidence rows; reads
assemble the aggregate with the latest verdict and all evidence. Every
query is parameterized; identifiers are never built from input.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.application.ports.repositories import ClaimRepository
from app.domain.claim import Claim, Evidence


class PostgresClaimRepository(ClaimRepository):
    """ClaimRepository backed by PostgreSQL.

    Args:
        dsn: PostgreSQL connection string (service role bypasses RLS).
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def _connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def save(self, claim: Claim) -> Claim:
        """Insert the claim, verdict, and evidence rows for one aggregate."""
        with self._connect() as conn:
            conn.execute(
                """
                insert into public.claims
                    (id, analysis_id, claim_index, text, normalized_text)
                values (%s, %s, %s, %s, %s)
                """,
                (
                    claim.id,
                    claim.analysis_id,
                    claim.claim_index,
                    claim.text,
                    claim.normalized_text,
                ),
            )
            verdict_row = conn.execute(
                """
                insert into public.claim_verdicts
                    (claim_id, verdict, confidence, model, rationale)
                values (%s, %s, %s, %s, %s)
                returning id
                """,
                (
                    claim.id,
                    claim.verdict,
                    claim.confidence,
                    claim.model,
                    claim.rationale,
                ),
            ).fetchone()
            if verdict_row is None:
                raise RuntimeError("claim verdict insert returned no row")
            verdict_id = verdict_row["id"]
            for evidence in claim.evidence:
                conn.execute(
                    """
                    insert into public.evidence
                        (id, verdict_id, kind, url, quote, snippet, relevance)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        evidence.id,
                        verdict_id,
                        evidence.kind,
                        evidence.url,
                        evidence.quote,
                        evidence.snippet,
                        evidence.relevance,
                    ),
                )
        return claim

    def get(self, claim_id: UUID) -> Claim | None:
        """Fetch one claim with its latest verdict and all evidence."""
        with self._connect() as conn:
            row: dict[str, Any] | None = conn.execute(
                """
                select c.id, c.analysis_id, c.claim_index, c.text, c.normalized_text,
                       v.verdict, v.confidence, v.model, v.rationale
                from public.claims c
                join public.claim_verdicts v on v.claim_id = c.id
                where c.id = %s
                order by v.created_at desc
                limit 1
                """,
                (claim_id,),
            ).fetchone()
            if row is None:
                return None
            evidence_rows = conn.execute(
                """
                select e.id, e.kind, e.url, e.quote, e.snippet, e.relevance
                from public.evidence e
                join public.claim_verdicts v on v.id = e.verdict_id
                where v.claim_id = %s
                order by e.id
                """,
                (claim_id,),
            ).fetchall()
        return Claim(
            analysis_id=row["analysis_id"],
            id=row["id"],
            claim_index=row["claim_index"],
            text=row["text"],
            normalized_text=row["normalized_text"],
            verdict=row["verdict"],
            confidence=row["confidence"],
            rationale=row["rationale"],
            model=row["model"] or "",
            evidence=tuple(
                Evidence(
                    id=evidence["id"],
                    kind=evidence["kind"],
                    url=evidence["url"],
                    quote=evidence["quote"],
                    snippet=evidence["snippet"],
                    relevance=evidence["relevance"],
                )
                for evidence in evidence_rows
            ),
        )

    def list_by_analysis(self, analysis_id: UUID) -> list[Claim]:
        """Fetch the claims of one analysis, in claim order."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id from public.claims
                where analysis_id = %s
                order by claim_index
                """,
                (analysis_id,),
            ).fetchall()
        return [claim for claim in (self.get(row["id"]) for row in rows) if claim]
