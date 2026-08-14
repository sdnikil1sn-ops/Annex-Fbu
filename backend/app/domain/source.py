"""Source aggregate — publisher/domain registry with credibility.

Phase 14 persisted ``sources`` / ``source_scores``; the aggregate carries
the latest credibility score and its trust signals so the API can render
a source profile in one read. Phase 19 adds community credibility
feedback: authenticated users rate a source 1–5, and the profile carries
the aggregated community signal (count + average) next to the model
score — the registry grows more accurate the more it is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class SourceFeedback:
    """Aggregated community credibility signal for a source (Phase 19).

    Attributes:
        count: Number of distinct users who rated the source.
        average: Mean rating (1–5), or None when nobody has rated yet.
        my_rating: The caller's own rating, when the profile was read
            for an authenticated user who has rated the source.
    """

    count: int = 0
    average: float | None = None
    my_rating: int | None = None


@dataclass(frozen=True)
class Source:
    """A publisher/domain with its latest credibility score.

    Attributes:
        id: Primary key of the ``sources`` row.
        domain: The publisher's domain (unique).
        name: Display name, when known.
        country: Country of origin, when known.
        language: Primary language, when known.
        category: Publisher category (news, fact_check, blog, ...).
        score: Latest model credibility score (0..1), when computed.
        signals: Named trust signals backing the score.
        model: Which model/version produced the latest score.
        computed_at: When the latest score was computed.
        community: Aggregated community credibility feedback (Phase 19),
            or None when feedback has not been loaded.
    """

    id: UUID
    domain: str
    name: str | None = None
    country: str | None = None
    language: str | None = None
    category: str | None = None
    score: float | None = None
    signals: dict[str, Any] | None = None
    model: str | None = None
    computed_at: datetime | None = None
    community: SourceFeedback | None = None
