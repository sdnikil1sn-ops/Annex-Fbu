"""In-memory SourceRepository for unit tests (explicit mock)."""

from __future__ import annotations

from uuid import uuid4

from app.application.ports.repositories import SourceRepository
from app.domain.source import Source


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
    """A deterministic in-memory store implementing the source port."""

    def __init__(self, seed: list[Source] | None = None) -> None:
        self._by_domain = {source.domain: source for source in (seed or _seed())}

    def get_by_domain(self, domain: str) -> Source | None:
        """Return the matching source or None."""
        return self._by_domain.get(domain)

    def search(self, query: str, *, limit: int = 20) -> list[Source]:
        """Case-insensitive substring match on domain or name."""
        lowered = query.lower()
        matches = [
            source
            for source in self._by_domain.values()
            if lowered in source.domain or (source.name or "").lower().find(lowered) >= 0
        ]
        matches.sort(key=lambda s: s.domain)
        return matches[:limit]
