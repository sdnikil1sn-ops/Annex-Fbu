"""Source service — queries the publisher/domain registry (Phase 14)."""

from __future__ import annotations

from app.application.ports.repositories import SourceRepository
from app.domain.source import Source


class SourceService:
    """Coordinates reads of the public sources/source_scores registry."""

    def __init__(self, repository: SourceRepository) -> None:
        self._repository = repository

    def get_profile(self, domain: str) -> Source | None:
        """Fetch one source profile with its latest credibility score."""
        return self._repository.get_by_domain(domain)

    def search(self, query: str, *, limit: int = 20) -> list[Source]:
        """Search sources by domain or name, best matches first."""
        return self._repository.search(query, limit=limit)
