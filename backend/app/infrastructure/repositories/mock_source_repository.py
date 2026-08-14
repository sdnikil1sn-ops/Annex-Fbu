"""In-memory SourceRepository for unit tests (explicit mock)."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.application.ports.repositories import SourceRepository
from app.domain.source import Source, SourceFeedback


def _seed() -> list[Source]:
    """A small deterministic registry mirroring the seed migration."""
    return [
        Source(
            id=uuid4(),
            domain="reuters.com",
            name="Reuters",
            country="US",
            language="en",
            category="news",
            score=0.92,
            signals={"editorial_standards": "high", "fact_checking": "strong"},
            model="seed-v1",
        ),
        Source(
            id=uuid4(),
            domain="conspiracy-news.net",
            name="Conspiracy News",
            country="US",
            language="en",
            category="blog",
            score=0.18,
            signals={"editorial_standards": "low", "fact_checking": "none"},
            model="seed-v1",
        ),
    ]


class MockSourceRepository(SourceRepository):
    """A deterministic in-memory store implementing the source port.

    Mirrors the PostgreSQL shape: ``source_feedback`` is one rating per
    (source, user); re-rating updates the row, and reads attach the
    count/average aggregate plus the caller's own rating.
    """

    def __init__(self, seed: list[Source] | None = None) -> None:
        self._by_domain = {source.domain: source for source in (seed or _seed())}
        # (domain, user_id) -> rating
        self._feedback: dict[tuple[str, UUID], int] = {}

    def seed_feedback(self, domain: str, user_id: UUID, rating: int) -> None:
        """Pre-populate one credibility rating (test helper)."""
        self._feedback[(domain, user_id)] = rating

    def get_by_domain(
        self, domain: str, *, user_id: UUID | None = None
    ) -> Source | None:
        """Return the matching source with community feedback attached."""
        source = self._by_domain.get(domain)
        if source is None:
            return None
        return self._with_community(source, user_id)

    def search(
        self, query: str, *, limit: int = 20, user_id: UUID | None = None
    ) -> list[Source]:
        """Case-insensitive substring match on domain or name."""
        lowered = query.lower()
        matches = [
            source
            for source in self._by_domain.values()
            if lowered in source.domain or (source.name or "").lower().find(lowered) >= 0
        ]
        matches.sort(key=lambda s: s.domain)
        return [self._with_community(source, user_id) for source in matches[:limit]]

    def rate(self, domain: str, user_id: UUID, rating: int) -> Source | None:
        """Record one user's rating; re-rating updates the row."""
        if domain not in self._by_domain:
            return None
        self._feedback[(domain, user_id)] = rating
        return self.get_by_domain(domain, user_id=user_id)

    # --- internals -------------------------------------------------------

    def _with_community(
        self, source: Source, user_id: UUID | None
    ) -> Source:
        ratings = [
            rating for (domain, _user), rating in self._feedback.items()
            if domain == source.domain
        ]
        average = (
            round(sum(ratings) / len(ratings), 2) if ratings else None
        )
        my_rating = self._feedback.get((source.domain, user_id)) if user_id else None
        return Source(
            id=source.id,
            domain=source.domain,
            name=source.name,
            country=source.country,
            language=source.language,
            category=source.category,
            score=source.score,
            signals=source.signals,
            model=source.model,
            computed_at=source.computed_at,
            community=SourceFeedback(
                count=len(ratings),
                average=average,
                my_rating=my_rating,
            ),
        )
