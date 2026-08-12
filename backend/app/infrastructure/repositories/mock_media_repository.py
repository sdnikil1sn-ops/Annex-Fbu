"""In-memory MediaRepository for unit tests (explicit mock)."""

from __future__ import annotations

from uuid import UUID

from app.application.ports.repositories import MediaRepository
from app.domain.media import MediaItem


class MockMediaRepository(MediaRepository):
    """A deterministic in-memory store implementing the media port."""

    def __init__(self) -> None:
        self._store: dict[UUID, MediaItem] = {}

    def save(self, item: MediaItem) -> MediaItem:
        """Store and return the media item."""
        self._store[item.id] = item
        return item

    def get(self, media_id: UUID) -> MediaItem | None:
        """Return the stored media item or None."""
        return self._store.get(media_id)
