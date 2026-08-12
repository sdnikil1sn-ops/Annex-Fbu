"""API tests for the v1 media endpoints (Phase 14)."""

from __future__ import annotations

import base64
from uuid import uuid4

from app.application.ports.media import ForensicsReport
from app.application.services.analysis_service import AnalysisService
from app.application.services.media_service import MediaService
from app.domain.analysis import AnalysisInputType
from app.infrastructure.media.mock_media_adapters import (
    MockForensicsAdapter,
    MockOcrAdapter,
)
from app.infrastructure.repositories.mock_analysis_repository import (
    MockAnalysisRepository,
)
from app.infrastructure.repositories.mock_media_repository import MockMediaRepository
from app.main import create_app
from fastapi.testclient import TestClient

PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-png").decode()


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _app(settings, token_verifier, user_service, *, analysis_service=None):
    """An app with the media service wired to deterministic adapters."""
    media_service = MediaService(
        MockMediaRepository(),
        ocr_adapter=MockOcrAdapter(),
        forensics_adapter=MockForensicsAdapter(
            report=ForensicsReport(
                signals={"width": 64, "height": 48, "ela_mean": 1.0},
                risk_score=0.1,
            )
        ),
    )
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=analysis_service or AnalysisService(MockAnalysisRepository()),
        media_service=media_service,
    )
    return app


def test_submit_and_get_media(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """An owned analysis can ingest media and read it back."""
    analysis_service = AnalysisService(MockAnalysisRepository())
    app = _app(
        settings,
        token_verifier,
        user_service,
        analysis_service=analysis_service,
    )
    analysis = analysis_service.submit(
        AnalysisInputType.TEXT, user_id=verified_identity.uid, content="x"
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/media",
            json={"analysis_id": str(analysis.analysis_id), "image": PNG_B64},
            headers=_headers(),
        )

        assert response.status_code == 201
        data = response.json()["data"]
        assert data["mime"] == "image/png"
        assert data["width"] == 64 and data["height"] == 48
        assert data["size_bytes"] == len(base64.b64decode(PNG_B64))
        assert data["ocr"]["raw_text"] == "mock ocr text"
        assert data["forensics"]["risk_score"] == 0.1
        assert data["forensics"]["model"] == "opencv-ela-v1"

        fetched = client.get(f"/api/v1/media/{data['id']}", headers=_headers())
    assert fetched.status_code == 200
    assert fetched.json()["data"]["id"] == data["id"]


def test_submit_media_requires_owned_analysis(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """Media can only attach to an analysis the caller owns."""
    analysis_service = AnalysisService(MockAnalysisRepository())
    app = _app(
        settings,
        token_verifier,
        user_service,
        analysis_service=analysis_service,
    )
    # Owned by someone else.
    foreign = analysis_service.submit(
        AnalysisInputType.TEXT, user_id=uuid4(), content="x"
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/media",
            json={"analysis_id": str(foreign.analysis_id), "image": PNG_B64},
            headers=_headers(),
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "media.analysis_not_found"


def test_submit_media_rejects_invalid_image(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """Base64 garbage is rejected at the API boundary."""
    analysis_service = AnalysisService(MockAnalysisRepository())
    app = _app(
        settings,
        token_verifier,
        user_service,
        analysis_service=analysis_service,
    )
    analysis = analysis_service.submit(
        AnalysisInputType.TEXT, user_id=verified_identity.uid, content="x"
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/media",
            json={"analysis_id": str(analysis.analysis_id), "image": "!!!not-base64!!!"},
            headers=_headers(),
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_image"


def test_submit_media_requires_token(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """Media ingestion requires a bearer token."""
    app = _app(settings, token_verifier, user_service)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/media",
            json={"analysis_id": str(uuid4()), "image": PNG_B64},
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_get_foreign_media_is_404(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """Another user's media reads as a 404."""
    analysis_service = AnalysisService(MockAnalysisRepository())
    app = _app(
        settings,
        token_verifier,
        user_service,
        analysis_service=analysis_service,
    )
    foreign = analysis_service.submit(
        AnalysisInputType.TEXT, user_id=uuid4(), content="x"
    )
    media_service = app.state.media_service
    item = media_service.ingest(
        analysis_id=foreign.analysis_id, image_bytes=base64.b64decode(PNG_B64)
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/media/{item.id}", headers=_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "media.not_found"


def test_media_not_configured_returns_503(authed_client: TestClient) -> None:
    """Without a wired media service, the endpoints answer 503."""
    response = authed_client.post(
        "/api/v1/media",
        json={"analysis_id": str(uuid4()), "image": PNG_B64},
        headers=_headers(),
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "media.not_configured"
