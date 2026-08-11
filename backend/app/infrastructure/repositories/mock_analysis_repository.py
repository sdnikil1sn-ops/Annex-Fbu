"""In-memory AnalysisRepository for unit tests.

This is an explicit mock (per CONTRIBUTING.md naming rules): it lives
behind the same port as the PostgreSQL implementation and is never used in
production code paths.
"""

from __future__ import annotations

from uuid import UUID

from app.application.ports.repositories import AnalysisRepository, Cursor
from app.domain.analysis import Analysis


class MockAnalysisRepository(AnalysisRepository):
    """A deterministic in-memory store implementing the repository port."""

    def __init__(self) -> None:
        self._store: dict[UUID, Analysis] = {}

    def create(self, analysis: Analysis) -> Analysis:
        """Store and return the analysis."""
        self._store[analysis.analysis_id] = analysis
        return analysis

    def get(self, analysis_id: UUID) -> Analysis | None:
        """Return the stored analysis or None."""
        return self._store.get(analysis_id)

    def list_by_user(
        self, user_id: UUID, *, limit: int = 50, cursor: Cursor | None = None
    ) -> list[Analysis]:
        """Return a user's analyses newest-first (mirrors the SQL ordering)."""
        items = [a for a in self._store.values() if a.user_id == user_id]
        items.sort(key=lambda a: (a.created_at, a.analysis_id), reverse=True)
        if cursor is not None:
            items = [a for a in items if (a.created_at, a.analysis_id) < cursor]
        return items[:limit]

    def update_status(self, analysis: Analysis) -> Analysis:
        """Replace the stored row with the updated state."""
        self._store[analysis.analysis_id] = analysis
        return analysis

    def delete(self, analysis_id: UUID) -> bool:
        """Remove an analysis; returns True when it existed."""
        return self._store.pop(analysis_id, None) is not None
