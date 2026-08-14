"""Sources endpoints — v1 contract (Phase 14, extended in Phase 19).

The publisher/domain registry is public-read (RLS policy matrix): source
profiles expose the latest credibility score and, since Phase 19, the
aggregated community credibility signal (count + average). Any
authenticated user can rate a source 1–5; the more the registry is used,
the more accurate the community picture becomes. Reads are public; the
profile includes the caller's own rating when a token is supplied.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_optional_user, get_source_service_dep
from app.api.errors import AppError
from app.application.services.source_service import SourceService
from app.domain.source import Source
from app.domain.user import User

router = APIRouter(prefix="/sources", tags=["sources"])


class RateSourceRequest(BaseModel):
    """Body for ``POST /sources/{domain}/rate``."""

    rating: int = Field(ge=1, le=5)


def _source_payload(source: Source) -> dict[str, Any]:
    community = source.community
    return {
        "id": str(source.id),
        "domain": source.domain,
        "name": source.name,
        "country": source.country,
        "language": source.language,
        "category": source.category,
        "score": source.score,
        "signals": source.signals,
        "model": source.model,
        "computed_at": source.computed_at.isoformat() if source.computed_at else None,
        "community": {
            "count": community.count if community else 0,
            "average": community.average if community else None,
            "my_rating": community.my_rating if community else None,
        },
    }


@router.get("/search")
def search_sources(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    user: User | None = Depends(get_optional_user),
    service: SourceService = Depends(get_source_service_dep),
) -> dict[str, Any]:
    """Search sources by domain or name (case-insensitive substring)."""
    sources = service.search(q, limit=limit, user_id=user.id if user else None)
    return {"data": [_source_payload(source) for source in sources]}


@router.get("/{domain}")
def get_source(
    domain: str,
    user: User | None = Depends(get_optional_user),
    service: SourceService = Depends(get_source_service_dep),
) -> dict[str, Any]:
    """Fetch one source profile with its credibility score.

    Public read: the profile carries the community aggregate; when the
    caller supplies a token, it also includes their own rating.
    """
    source = service.get_profile(domain, user_id=user.id if user else None)
    if source is None:
        raise AppError("source.not_found", "Source not found.", status_code=404)
    return {"data": _source_payload(source)}


@router.post("/{domain}/rate", status_code=200)
def rate_source(
    domain: str,
    body: RateSourceRequest,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_source_service_dep),
) -> dict[str, Any]:
    """Rate a source's credibility (1–5), updating the community signal.

    Re-rating replaces the caller's own rating (one voice per user); the
    response carries the updated profile with the aggregated community
    count and average.
    """
    source = service.rate(domain, user.id, body.rating)
    if source is None:
        raise AppError("source.not_found", "Source not found.", status_code=404)
    return {"data": _source_payload(source)}
