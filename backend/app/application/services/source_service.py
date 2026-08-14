"""Source service — queries the publisher/domain registry (Phase 14).

Phase 19 adds community credibility feedback: an authenticated user rates
a source's credibility (1–5), and the profile aggregates the community
signal next to the model score — the registry grows more accurate the
more it is used. Authorization (only the caller's own rating may be
written) is enforced at the service boundary.
"""

from __future__ import annotations

from uuid import UUID

from app.application.ports.repositories import SourceRepository
from app.domain.source import Source


class SourceService:
    """Coordinates reads and community feedback on the source registry."""

    def __init__(self, repository: SourceRepository) -> None:
        self._repository = repository

    def get_profile(self, domain: str, user_id: UUID | None = None) -> Source | None:
        """Fetch one source profile with its latest credibility score.

        Args:
            domain: The publisher's domain.
            user_id: Optional caller id; the profile then carries their
                own rating as ``community.my_rating``.
        """
        return self._repository.get_by_domain(domain, user_id=user_id)

    def search(
        self, query: str, *, limit: int = 20, user_id: UUID | None = None
    ) -> list[Source]:
        """Search sources by domain or name, best matches first."""
        return self._repository.search(query, limit=limit, user_id=user_id)

    def rate(self, domain: str, user_id: UUID, rating: int) -> Source | None:
        """Record one user's credibility rating for a source (1–5).

        Re-rating updates the caller's own row — one voice per user. The
        returned profile carries the updated community aggregate. Returns
        None when the source does not exist.
        """
        return self._repository.rate(domain, user_id, rating)
