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
from app.domain.classroom import (
    Assignment,
    AssignmentProgress,
    ClassMember,
    ClassRoom,
)
from app.domain.i18n import (
    I18nLocale,
    MissingKey,
    TranslationEntry,
    TranslationSuggestion,
)
from app.domain.lesson import Lesson, LessonProgress
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

    ``publish_translation`` (Phase 18) upserts one entry and bumps its
    version so bundle versions shift and clients refresh — the path
    approved community suggestions take to reach the live bundles.
    """

    def list_locales(self) -> list[I18nLocale]: ...

    def translations_for(self, locale_code: str) -> list[TranslationEntry]: ...

    def publish_translation(
        self,
        locale_code: str,
        namespace: str,
        key: str,
        value: str,
        plural_rule: str = "none",
    ) -> TranslationEntry | None: ...


class TranslationSuggestionRepository(Protocol):
    """Persistence contract for community translation suggestions (Phase 18).

    ``translation_suggestions`` is a review queue: contributors submit
    proposed values for keys, moderators approve or reject them, and an
    approved suggestion is published into ``i18n_translations`` (with a
    version bump) by the service via the I18nRepository. One pending
    suggestion per (user, locale, key) keeps the queue clean — a
    re-submission updates the contributor's own pending row.
    """

    def list_missing(
        self, locale_code: str, default_locale: str = "en"
    ) -> list[MissingKey]: ...

    def submit(self, suggestion: TranslationSuggestion) -> TranslationSuggestion | None: ...

    def get(self, suggestion_id: UUID) -> TranslationSuggestion | None: ...

    def list_for_user(
        self, user_id: UUID, *, status: str | None = None
    ) -> list[TranslationSuggestion]: ...

    def list_pending(self, *, limit: int = 50) -> list[TranslationSuggestion]: ...

    def review(
        self, suggestion_id: UUID, reviewer_id: UUID, approved: bool
    ) -> TranslationSuggestion | None: ...


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


class LessonRepository(Protocol):
    """Persistence contract for the education curriculum (Phase 15).

    Content is resolved for the best available locale in the caller's
    fallback chain (ADR-0007): the repository picks the content row whose
    locale appears earliest in ``chain`` (requested → parent → default).
    Progress rows are joined per user, so list/get return the aggregate
    with completion state attached.
    """

    def list_lessons(
        self, *, chain: list[str], user_id: UUID | None = None
    ) -> list[Lesson]: ...

    def get_lesson(
        self, lesson_id: UUID, *, chain: list[str], user_id: UUID | None = None
    ) -> Lesson | None: ...

    def get_by_slug(
        self, slug: str, *, chain: list[str], user_id: UUID | None = None
    ) -> Lesson | None: ...

    def mark_complete(self, user_id: UUID, lesson_id: UUID) -> LessonProgress: ...


class ClassRepository(Protocol):
    """Persistence contract for educator classes (Phase 17).

    Class rows carry the teacher as ``owner_id`` and the owner is also
    inserted into ``class_members`` with role ``teacher``, so membership
    is the single source of truth for who may act on a class. Progress
    reports join members against ``lesson_progress`` (Phase 15) — no
    separate progress store exists.
    """

    def create_class(
        self,
        owner_id: UUID,
        name: str,
        description: str,
        invite_code: str,
    ) -> ClassRoom: ...

    def list_classes(self, user_id: UUID) -> list[ClassRoom]: ...

    def get_class(self, class_id: UUID, user_id: UUID) -> ClassRoom | None: ...

    def membership_role(self, class_id: UUID, user_id: UUID) -> str | None: ...

    def join_class(self, invite_code: str, user_id: UUID) -> ClassMember | None: ...

    def resolve_lesson(self, lesson_ref: str) -> UUID | None: ...

    def assign_lesson(
        self,
        class_id: UUID,
        lesson_id: UUID,
        assigned_by: UUID,
        due_at: datetime | None,
    ) -> Assignment | None: ...

    def list_assignments(self, class_id: UUID) -> list[Assignment]: ...

    def get_assignment(self, class_id: UUID, assignment_id: UUID) -> Assignment | None: ...

    def delete_assignment(self, class_id: UUID, assignment_id: UUID) -> bool: ...

    def assignment_progress(
        self, class_id: UUID, assignment_id: UUID
    ) -> AssignmentProgress | None: ...

    def class_progress(self, class_id: UUID) -> list[AssignmentProgress]: ...

    def remove_member(self, class_id: UUID, member_id: UUID) -> bool: ...

    def delete_class(self, class_id: UUID) -> bool: ...
