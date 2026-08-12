"""Repository ports (ADR-0003, ADR-0004).

Repositories abstract all persistence; application code depends on these
protocols and never touches SQL or clients directly. Implementations live
in ``app.infrastructure.repositories``.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.application.ports.auth import VerifiedIdentity
from app.domain.analysis import Analysis
from app.domain.claim import Claim
from app.domain.i18n import I18nLocale, TranslationEntry
from app.domain.media import MediaItem
from app.domain.source import Source
from app.domain.user import User

# Cursor for cursor-based pagination: the (created_at, id) of the last
# row returned, matching the list ordering (created_at desc, id desc).
Cursor = tuple[datetime, UUID]


class UserRepository(Protocol):
    """Persistence contract for the User aggregate."""

    def ensure_user(self, identity: VerifiedIdentity) -> None:
        """Insert the user and their default profile when absent."""
        ...

    def get_by_id(self, user_id: UUID) -> User | None:
        """Fetch a user with their current role, or None when absent."""
        ...


class I18nRepository(Protocol):
    """Persistence contract for runtime i18n (ADR-0007).

    Locales are the enabled set only; disabled locales are invisible to
    clients (their bundles answer 404). Translations are fetched per
    locale and merged into bundles by the service.
    """

    def list_locales(self) -> list[I18nLocale]: ...

    def translations_for(self, locale_code: str) -> list[TranslationEntry]: ...


class AnalysisRepository(Protocol):
    """Persistence contract for the Analysis aggregate."""

    def create(self, analysis: Analysis) -> Analysis: ...

    def get(self, analysis_id: UUID) -> Analysis | None: ...

    def list_by_user(
        self, user_id: UUID, *, limit: int = 50, cursor: Cursor | None = None
    ) -> list[Analysis]: ...

    def update_status(self, analysis: Analysis) -> Analysis: ...

    def delete(self, analysis_id: UUID) -> bool: ...


class ClaimRepository(Protocol):
    """Persistence contract for the Claim aggregate (Phase 14).

    ``save`` persists the claim row, its verdict row, and its evidence
    rows; ``get`` returns the claim with its latest verdict and evidence;
    ``list_by_analysis`` feeds the idempotency guard so redelivered
    completions never duplicate claims.
    """

    def save(self, claim: Claim) -> Claim: ...

    def get(self, claim_id: UUID) -> Claim | None: ...

    def list_by_analysis(self, analysis_id: UUID) -> list[Claim]: ...


class SourceRepository(Protocol):
    """Persistence contract for the Source registry (Phase 14).

    Sources are public-read (RLS policy matrix); writes happen through
    the service role only (seeding, background scoring).
    """

    def get_by_domain(self, domain: str) -> Source | None: ...

    def search(self, query: str, *, limit: int = 20) -> list[Source]: ...


class MediaRepository(Protocol):
    """Persistence contract for media items with OCR + forensics (Phase 14).

    ``save`` persists the media item and its OCR/forensics children;
    ``get`` returns the aggregate with its children attached.
    """

    def save(self, item: MediaItem) -> MediaItem: ...

    def get(self, media_id: UUID) -> MediaItem | None: ...
