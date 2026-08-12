"""Analysis endpoints — v1 contract: docs/api/v1-endpoints.md.

Submitting an analysis runs the claim-analysis pipeline inline through the
bound analyzer and persists the report (interim synchronous path; ADR-0008
moves processing into Celery workers). The API keeps the documented
``202 + analysis_id`` contract either way, so clients poll
``GET /analysis/{id}`` for the report.
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import (
    get_analysis_service_dep,
    get_claim_analyzer_dep,
    get_current_user,
    get_optional_user,
)
from app.api.errors import AppError
from app.application.ports.ai import ClaimAnalyzer
from app.application.ports.repositories import Cursor
from app.application.services.analysis_service import AnalysisService
from app.domain.analysis import Analysis, AnalysisInputType, AnalysisStatus
from app.domain.user import User

router = APIRouter(prefix="/analysis", tags=["analysis"])


class SubmitAnalysisRequest(BaseModel):
    """Body for ``POST /analysis``."""

    input_type: AnalysisInputType = AnalysisInputType.TEXT
    text: str = Field(min_length=1, max_length=20_000)
    locale: str = Field(default="en", min_length=2, max_length=10)


def _analysis_payload(analysis: Analysis) -> dict[str, Any]:
    """Serialize an analysis into the API shape."""
    return {
        "id": str(analysis.analysis_id),
        "input_type": analysis.input_type.value,
        "status": analysis.status.value,
        "locale": analysis.locale,
        "failure_reason": analysis.failure_reason,
        "report": analysis.report,
        "created_at": analysis.created_at.isoformat(),
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
    }


def _retry_meta(analysis: Analysis) -> dict[str, Any]:
    """Include a polite poll interval while the analysis is not terminal."""
    if analysis.status in {AnalysisStatus.PENDING, AnalysisStatus.PROCESSING}:
        return {"retry_after": 5}
    return {}


def _encode_cursor(analysis: Analysis) -> str:
    """Encode a (created_at, id) cursor into an opaque, URL-safe string."""
    raw = f"{analysis.created_at.isoformat()}|{analysis.analysis_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(value: str) -> Cursor:
    """Decode a cursor string back into a (created_at, id) tuple."""
    try:
        raw = base64.urlsafe_b64decode(value.encode()).decode()
        created_at, analysis_id = raw.split("|", 1)
        return datetime.fromisoformat(created_at), UUID(analysis_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AppError(
            "validation.invalid_cursor",
            "The cursor is malformed.",
            status_code=400,
        ) from exc


@router.post("", status_code=202)
def submit(
    body: SubmitAnalysisRequest,
    user: User | None = Depends(get_optional_user),
    service: AnalysisService = Depends(get_analysis_service_dep),
    analyzer: ClaimAnalyzer = Depends(get_claim_analyzer_dep),
) -> dict[str, Any]:
    """Submit content for claim analysis (text only at this phase).

    Accepts anonymous submissions; anonymous analyses carry no owner and can
    only be read back by their holder while unauthenticated context exists.
    Returns 202 with the analysis so clients can poll for the report.
    """
    if body.input_type is not AnalysisInputType.TEXT:
        raise AppError(
            "analysis.unsupported_input",
            "Only text input is supported at this time.",
            status_code=400,
            details={"supported": ["text"]},
        )
    analysis = service.analyze_text(
        body.text,
        analyzer=analyzer,
        input_type=body.input_type,
        user_id=user.id if user else None,
        locale=body.locale,
    )
    return {"data": _analysis_payload(analysis), "meta": _retry_meta(analysis)}


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: UUID,
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service_dep),
) -> dict[str, Any]:
    """Fetch one analysis with its report (owner only)."""
    analysis = service.get(analysis_id)
    if analysis is None or analysis.user_id != user.id:
        # Do not reveal whether the analysis exists.
        raise AppError("analysis.not_found", "Analysis not found.", status_code=404)
    return {"data": _analysis_payload(analysis), "meta": _retry_meta(analysis)}


@router.get("")
def list_analyses(
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service_dep),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, Any]:
    """List the caller's analyses, newest first (cursor-paginated)."""
    decoded = _decode_cursor(cursor) if cursor else None
    analyses = service.list_for_user(user.id, limit=limit, cursor=decoded)
    next_cursor = _encode_cursor(analyses[-1]) if len(analyses) == limit else None
    return {
        "data": [_analysis_payload(analysis) for analysis in analyses],
        "meta": {"next_cursor": next_cursor},
    }


@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: UUID,
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends(get_analysis_service_dep),
) -> dict[str, Any]:
    """Delete an analysis (owner only)."""
    analysis = service.get(analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise AppError("analysis.not_found", "Analysis not found.", status_code=404)
    service.delete(analysis_id)
    return {"data": {"deleted": str(analysis_id)}}
