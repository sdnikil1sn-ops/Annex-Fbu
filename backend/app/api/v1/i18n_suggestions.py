"""Community translation suggestion endpoints — v1 contract (Phase 18).

Extends runtime i18n (ADR-0007): contributors list untranslated keys
for an enabled locale, propose translations, and moderators approve or
reject them. An approved suggestion is published into the live
``i18n_translations`` store with a version bump, so clients pick the new
value up over the air — adding a language (or filling one out) stays a
data change, never a rebuild.

Authorization: submissions require a token; review and the pending queue
require the ``moderator`` (or ``admin``) role. The missing-keys listing
is public like the bundle endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_user,
    get_translation_suggestion_service_dep,
    require_roles,
)
from app.api.errors import AppError
from app.application.services.translation_suggestion_service import (
    TranslationSuggestionService,
)
from app.domain.i18n import TranslationSuggestion
from app.domain.user import User

router = APIRouter(prefix="/i18n/suggestions", tags=["i18n"])

# Reviewer gate shared by the review endpoints (module-level so ruff's
# B008 accepts the function call, per the project's FastAPI convention).
moderator_only = Depends(require_roles("moderator", "admin"))


class SubmitSuggestionRequest(BaseModel):
    """Body for ``POST /i18n/suggestions``."""

    locale: str = Field(min_length=2, max_length=16)
    namespace: str = Field(min_length=1, max_length=64)
    key: str = Field(min_length=1, max_length=128)
    value: str = Field(min_length=1, max_length=1_000)
    plural_rule: str = Field(default="none", pattern=r"^(none|zero|one|two|few|many|other)$")


class ReviewSuggestionRequest(BaseModel):
    """Body for ``POST /i18n/suggestions/{id}/review``."""

    approved: bool


def _suggestion_payload(suggestion: TranslationSuggestion) -> dict[str, Any]:
    return {
        "id": str(suggestion.id),
        "locale": suggestion.locale_code,
        "namespace": suggestion.namespace,
        "key": suggestion.key,
        "value": suggestion.value,
        "plural_rule": suggestion.plural_rule,
        "suggested_by": str(suggestion.suggested_by) if suggestion.suggested_by else None,
        "status": suggestion.status,
        "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
        "reviewed_by": str(suggestion.reviewed_by) if suggestion.reviewed_by else None,
        "reviewed_at": suggestion.reviewed_at.isoformat() if suggestion.reviewed_at else None,
    }


@router.get("/missing")
def list_missing(
    locale: str = Query(min_length=2, max_length=16),
    default_locale: str = Query(default="en", min_length=2, max_length=16),
    service: TranslationSuggestionService = Depends(get_translation_suggestion_service_dep),
) -> dict[str, Any]:
    """List keys the default locale defines that ``locale`` lacks.

    Public, like the bundle endpoints. The contributor uses this to pick
    what to translate; approved suggestions stop being missing naturally.
    """
    missing = service.missing(locale, default_locale=default_locale)
    return {
        "data": [
            {
                "namespace": item.namespace,
                "key": item.key,
                "english": item.english_value,
            }
            for item in missing
        ],
        "meta": {"locale": locale, "count": len(missing)},
    }


@router.post("", status_code=201)
def submit_suggestion(
    body: SubmitSuggestionRequest,
    user: User = Depends(get_current_user),
    service: TranslationSuggestionService = Depends(get_translation_suggestion_service_dep),
) -> dict[str, Any]:
    """Submit a translation proposal for an enabled locale."""
    suggestion = service.submit(
        user.id,
        body.locale,
        body.namespace,
        body.key,
        body.value,
        plural_rule=body.plural_rule,
    )
    if suggestion is None:
        raise AppError(
            "i18n.locale_not_found",
            "The requested locale is not available.",
            status_code=404,
        )
    return {"data": _suggestion_payload(suggestion)}


@router.get("")
def list_own_suggestions(
    user: User = Depends(get_current_user),
    service: TranslationSuggestionService = Depends(get_translation_suggestion_service_dep),
    status: str | None = Query(default=None, pattern=r"^(pending|approved|rejected)$"),
) -> dict[str, Any]:
    """List the caller's suggestions, newest first (optional status filter)."""
    suggestions = service.list_for_user(user.id, status=status)
    return {"data": [_suggestion_payload(item) for item in suggestions]}


@router.get("/pending")
def list_pending(
    user: User = moderator_only,
    service: TranslationSuggestionService = Depends(get_translation_suggestion_service_dep),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List the moderator review queue, oldest first."""
    suggestions = service.list_pending(limit=limit)
    return {"data": [_suggestion_payload(item) for item in suggestions]}


@router.post("/{suggestion_id}/review")
def review_suggestion(
    suggestion_id: UUID,
    body: ReviewSuggestionRequest,
    user: User = moderator_only,
    service: TranslationSuggestionService = Depends(get_translation_suggestion_service_dep),
) -> dict[str, Any]:
    """Approve or reject a pending suggestion (moderator+).

    Approving publishes the value into ``i18n_translations`` with a
    version bump, so clients refresh without a release.
    """
    suggestion = service.review(suggestion_id, user.id, body.approved)
    if suggestion is None:
        raise AppError(
            "i18n.suggestion_not_found",
            "The suggestion does not exist or was already reviewed.",
            status_code=404,
        )
    return {"data": _suggestion_payload(suggestion)}
