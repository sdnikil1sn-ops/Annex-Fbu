"""Analysis endpoints — v1 contract: docs/api/v1-endpoints.md.

Submitting an analysis returns ``202 + analysis_id`` and the worker pool
(Phase 7, ADR-0008) processes it asynchronously — clients poll
``GET /analysis/{id}`` for the report. Without a broker the pipeline runs
inline through the bound analyzer (interim synchronous path) with the same
contract.

Since Phase 13 all three input types are supported: text, URL (fetched
server-side through the SSRF guard) and image (OCR + forensics).
"""

from __future__ import annotations

import base64
import binascii
import urllib.parse
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
    get_settings_dep,
)
from app.api.errors import AppError
from app.application.ports.ai import ClaimAnalyzer
from app.application.ports.repositories import Cursor
from app.application.services.analysis_service import AnalysisService
from app.core.config import Settings
from app.domain.analysis import Analysis, AnalysisInputType, AnalysisStatus
from app.domain.user import User

router = APIRouter(prefix="/analysis", tags=["analysis"])


class SubmitAnalysisRequest(BaseModel):
    """Body for ``POST /analysis``.

    Exactly one content field must be present, matching ``input_type``:

    - ``text`` for text input,
    - ``url`` for URL input (fetched server-side, SSRF-guarded),
    - ``image`` for image input — base64-encoded bytes or a ``data:`` URL;
      validated at the API boundary with a size cap, then OCR + forensics
      (the MIME type is sniffed from the bytes by the pipeline).
    """

    input_type: AnalysisInputType = AnalysisInputType.TEXT
    text: str | None = Field(default=None, min_length=1, max_length=20_000)
    url: str | None = Field(default=None, max_length=2_048)
    image: str | None = None
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
    settings: Settings = Depends(get_settings_dep),
) -> dict[str, Any]:
    """Submit text, a URL, or an image for claim analysis.

    Accepts anonymous submissions; anonymous analyses carry no owner and can
    only be read back by their holder while unauthenticated context exists.
    Returns 202 with the analysis so clients can poll for the report.
    """
    content = _prepare_content(body, settings)
    analysis = service.analyze(
        body.input_type,
        content=content,
        analyzer=analyzer,
        user_id=user.id if user else None,
        locale=body.locale,
    )
    return {"data": _analysis_payload(analysis), "meta": _retry_meta(analysis)}


def _prepare_content(body: SubmitAnalysisRequest, settings: Settings) -> str:
    """Validate the submission and normalize it into persisted content.

    Shape-only validation happens here (scheme, base64 decodability, size
    cap); the SSRF guard and image processing run later in the pipeline so
    DNS lookups and fetches never happen on the request path.

    Raises:
        AppError 400: the payload does not match the declared input type.
    """
    if body.input_type is AnalysisInputType.TEXT:
        if not body.text:
            raise AppError(
                "validation.invalid_input",
                "text is required for text input.",
                status_code=400,
            )
        return body.text

    if body.input_type is AnalysisInputType.URL:
        if not body.url:
            raise AppError(
                "validation.invalid_url",
                "url is required for url input.",
                status_code=400,
            )
        _validate_url(body.url)
        return body.url

    if body.input_type is AnalysisInputType.IMAGE:
        if not body.image:
            raise AppError(
                "validation.invalid_image",
                "image is required for image input.",
                status_code=400,
            )
        return _normalize_image(body.image, settings.media_image_max_bytes)

    raise AppError(
        "validation.invalid_input",
        "Unsupported input type.",
        status_code=400,
    )


def _validate_url(url: str) -> None:
    """Reject URLs that are not plain http(s) without credentials.

    The full SSRF guard (DNS + address checks) runs in the fetcher; this
    is the cheap shape check only.
    """
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise AppError(
            "validation.invalid_url",
            "url must be an http(s) address without embedded credentials.",
            status_code=400,
        )


def _normalize_image(image: str, max_bytes: int) -> str:
    """Strip a ``data:`` prefix if present and validate the base64 payload.

    Returns the canonical base64 string persisted as the analysis content.
    """
    if image.startswith("data:"):
        _, separator, image = image.partition(",")
        if not separator:
            raise AppError(
                "validation.invalid_image",
                "Malformed image data URL.",
                status_code=400,
            )
    # Cheap length pre-check before decoding: base64 inflates 4/3, so an
    # encoded payload over ~4/3 * max_bytes can never decode under the cap.
    # Rejecting here avoids base64-decoding a huge body on the request path.
    if len(image) > max_bytes * 4 // 3 + 4:
        raise AppError(
            "validation.invalid_image",
            f"image exceeds the {max_bytes}-byte size cap.",
            status_code=400,
        )
    try:
        payload = base64.b64decode(image, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AppError(
            "validation.invalid_image",
            "image must be valid base64-encoded bytes.",
            status_code=400,
        ) from exc
    if not payload:
        raise AppError(
            "validation.invalid_image",
            "image payload is empty.",
            status_code=400,
        )
    if len(payload) > max_bytes:
        raise AppError(
            "validation.invalid_image",
            f"image exceeds the {max_bytes}-byte size cap.",
            status_code=400,
        )
    return image


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
