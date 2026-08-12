"""Runtime i18n endpoints — v1 contract: docs/api/v1-endpoints.md.

Serves the enabled locales and versioned translation bundles (ADR-0007).
Bundles are resolved server-side over the fallback chain and cacheable:
clients send the bundle ``version`` (or ``If-None-Match`` with the ETag)
and receive ``304 Not Modified`` when nothing changed.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_i18n_service_dep, get_settings_dep
from app.api.errors import AppError
from app.application.services.i18n_service import I18nService
from app.core.config import Settings

router = APIRouter(prefix="/i18n", tags=["i18n"])

# BCP-47-ish: 2-3 letter language tag, optional script/region subtags.
_LOCALE_CODE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$")


def _normalize_locale(locale: str) -> str:
    """Validate and normalize a locale code from the URL path."""
    code = locale.strip().lower()
    if not _LOCALE_CODE.fullmatch(code):
        raise AppError(
            "validation.invalid_locale",
            "The locale code is malformed.",
            status_code=400,
            details={"pattern": "^[a-z]{2,3}(-[a-z0-9]{2,8})*$"},
        )
    return code


def _bundle_etag(locale: str, version: int) -> str:
    """Build the strong ETag identifying a bundle revision."""
    return f'"{locale}:{version}"'


@router.get("/locales")
def list_locales(
    service: I18nService = Depends(get_i18n_service_dep),
) -> dict[str, Any]:
    """Return every enabled locale with its fallback parent."""
    return {
        "data": {
            "default_locale": service.default_locale,
            "locales": [
                {"code": locale.code, "fallback_code": locale.fallback_code}
                for locale in service.list_locales()
            ],
        }
    }


@router.get("/bundles/{locale}")
def get_bundle(
    locale: str,
    request: Request,
    service: I18nService = Depends(get_i18n_service_dep),
    settings: Settings = Depends(get_settings_dep),
    version: int | None = Query(default=None, ge=1),
) -> Response:
    """Return a versioned translation bundle resolved over the fallback chain.

    Conditional requests: pass the previously received ``version`` as a
    query parameter (or ``If-None-Match`` with the bundle ETag) to receive
    ``304 Not Modified`` while the bundle is unchanged.
    """
    code = _normalize_locale(locale)
    bundle = service.bundle(code)
    if bundle is None:
        raise AppError(
            "i18n.locale_not_found",
            "The requested locale is not available.",
            status_code=404,
            details={"available": [item.code for item in service.list_locales()]},
        )

    etag = _bundle_etag(bundle.locale, bundle.version)
    headers = {
        "ETag": etag,
        "Cache-Control": f"public, max-age={settings.i18n_bundle_cache_ttl}",
    }
    cached = version == bundle.version or request.headers.get("if-none-match") == etag
    if cached:
        return Response(status_code=304, headers=headers)

    payload = {
        "data": {
            "locale": bundle.locale,
            "fallback_locale": bundle.fallback_locale,
            "version": bundle.version,
            "entries": {
                key: {"value": entry.value, "plural": entry.plural_rule}
                for key, entry in bundle.entries.items()
            },
        },
        "meta": {"etag": etag},
    }
    return JSONResponse(content=payload, headers=headers)
