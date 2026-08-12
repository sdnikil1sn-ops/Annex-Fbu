"""Integration tests: PostgresMediaRepository against a real database.

Gated on TEST_DATABASE_URL; the schema is applied from the versioned
migrations on every run (helpers.apply_migrations).
"""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from app.application.ports.repositories import MediaRepository
from app.domain.analysis import Analysis, AnalysisInputType
from app.domain.media import ForensicsRecord, MediaItem, OcrRecord
from app.infrastructure.repositories.analysis_repository import PostgresAnalysisRepository
from app.infrastructure.repositories.media_repository import PostgresMediaRepository

from tests.integration.helpers import apply_migrations, create_user

TEST_DSN = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL is not set")


@pytest.fixture()
def repository() -> MediaRepository:
    """A fresh-schema Postgres media repository per test."""
    apply_migrations(TEST_DSN)
    return PostgresMediaRepository(TEST_DSN)


@pytest.fixture()
def analysis_id() -> UUID:
    """An owned analysis row for media to reference."""
    owner = uuid4()
    create_user(TEST_DSN, owner)
    analysis = PostgresAnalysisRepository(TEST_DSN).create(
        Analysis(input_type=AnalysisInputType.IMAGE, user_id=owner, content="img")
    )
    return analysis.analysis_id


def test_save_and_get_round_trip(repository: MediaRepository, analysis_id: UUID) -> None:
    """A media item persists with OCR + forensics children and reads back."""
    item_id = uuid4()
    item = MediaItem(
        id=item_id,
        analysis_id=analysis_id,
        storage_path="inline/abc123.png",
        mime="image/png",
        sha256="abc123",
        width=64,
        height=48,
        size_bytes=1024,
        ocr=OcrRecord(
            media_item_id=item_id,
            language="eng",
            confidence=0.9,
            raw_text="hello",
        ),
        forensics=ForensicsRecord(
            media_item_id=item_id,
            signals={"ela_mean": 1.2, "width": 64},
            risk_score=0.1,
            model="opencv-ela-v1",
        ),
    )
    saved = repository.save(item)

    fetched = repository.get(saved.id)
    assert fetched is not None
    assert fetched.analysis_id == analysis_id
    assert fetched.storage_path == "inline/abc123.png"
    assert fetched.mime == "image/png"
    assert fetched.sha256 == "abc123"
    assert fetched.width == 64 and fetched.height == 48
    assert fetched.size_bytes == 1024
    assert fetched.ingested_at == item.ingested_at

    assert fetched.ocr is not None
    assert fetched.ocr.raw_text == "hello"
    assert fetched.ocr.confidence == 0.9
    assert fetched.ocr.language == "eng"

    assert fetched.forensics is not None
    assert fetched.forensics.risk_score == 0.1
    assert fetched.forensics.model == "opencv-ela-v1"
    assert fetched.forensics.signals == {"ela_mean": 1.2, "width": 64}


def test_get_missing_returns_none(repository: MediaRepository) -> None:
    """An unknown media id yields None, not an error."""
    assert repository.get(uuid4()) is None
