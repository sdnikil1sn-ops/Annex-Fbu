"""Versioned API router aggregating all v1 sub-routers.

New feature routers (analysis, claims, sources, users, media, i18n) are
included here as their phases land. Note: the unversioned health router is
mounted directly by the application factory (app.main), not here.
"""

from fastapi import APIRouter

from app.api.v1 import meta

api_router = APIRouter()
api_router.include_router(meta.router)
