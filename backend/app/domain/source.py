"""Source aggregate — publisher/domain registry with credibility (Phase 14).

Persisted into ``sources`` / ``source_scores``; the aggregate carries the
latest credibility score and its trust signals so the API can render a
source profile in one read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Source:
    """A publisher/domain with its latest credibility score."""

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
