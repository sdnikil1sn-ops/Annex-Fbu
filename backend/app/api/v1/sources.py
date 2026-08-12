"""Sources endpoints — v1 contract (Phase 14).

The publisher/domain registry is public-read (RLS policy matrix); these
endpoints expose source profiles with their latest credibility score and
support search by domain or name. No authentication is required.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_source_service_dep
from app.api.errors import AppError
from app.application.services.source_service import SourceService
from app.domain.source import Source

router = APIRouter(prefix="/sources", tags=["sources"])


def _source_payload(source: Source) -> dict[str, Any]:
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
    }


@router.get("/search")
def search_sources(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    service: SourceService = Depends(get_source_service_dep),
) -> dict[str, Any]:
    """Search sources by domain or name (case-insensitive substring)."""
    sources = service.search(q, limit=limit)
    return {"data": [_source_payload(source) for source in sources]}


@router.get("/{domain}")
def get_source(
    domain: str,
    service: SourceService = Depends(get_source_service_dep),
) -> dict[str, Any]:
    """Fetch one source profile with its credibility score."""
    source = service.get_profile(domain)
    if source is None:
        raise AppError("source.not_found", "Source not found.", status_code=404)
    return {"data": _source_payload(source)}
