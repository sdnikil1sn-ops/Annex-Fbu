"""API tests for the v1 claims endpoints (Phase 14)."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.application.ports.ai import ClaimAnalysis, ClaimItem
from app.application.services.analysis_service import AnalysisService
from app.application.services.claims_service import ClaimsService
from app.domain.analysis import Analysis, AnalysisInputType
from app.infrastructure.repositories.mock_analysis_repository import (
    MockAnalysisRepository,
)
from app.infrastructure.repositories.mock_claim_repository import MockClaimRepository
from app.main import create_app
from fastapi.testclient import TestClient


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _build(settings, token_verifier, user_service, *, owner_id):
    """An app whose analysis service persists claims on completion."""
    claim_repository = MockClaimRepository()
    claims_service = ClaimsService(claim_repository)
    analysis_service = AnalysisService(
        MockAnalysisRepository(),
        claims_service=claims_service,
    )
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=analysis_service,
        claims_service=claims_service,
    )
    return app, claims_service


def _complete_analysis(client: TestClient) -> dict:
    """Submit a text analysis as the test identity and return its payload."""
    response = client.post(
        "/api/v1/analysis", json={"text": "The sky is blue."}, headers=_headers()
    )
    assert response.status_code == 202
    return response.json()["data"]


def test_completed_analysis_exposes_claims(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """A completed analysis persists claims the owner can read back."""
    app, claims_service = _build(
        settings, token_verifier, user_service, owner_id=verified_identity.uid
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        data = _complete_analysis(client)
        analysis_id = UUID(data["id"])
        [claim] = claims_service._repository.list_by_analysis(analysis_id)

        response = client.get(f"/api/v1/claims/{claim.id}", headers=_headers())
        assert response.status_code == 200
        payload = response.json()["data"]
        assert payload["verdict"] == "partially_verifiable"
        assert payload["text"] == "mock claim"
        assert payload["analysis_id"] == data["id"]
        assert payload["confidence"] == 0.5
        assert payload["model"] == "mock"

        evidence = client.get(
            f"/api/v1/claims/{claim.id}/evidence", headers=_headers()
        )
        assert evidence.status_code == 200
        items = evidence.json()["data"]
        assert items == [
            {
                "id": str(claim.evidence[0].id),
                "kind": "link",
                "url": "https://example.com/evidence",
                "quote": None,
                "snippet": None,
                "relevance": 0.5,
            }
        ]


def test_get_foreign_claim_is_404(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """Another user's claim is indistinguishable from a missing one."""
    app, claims_service = _build(
        settings, token_verifier, user_service, owner_id=verified_identity.uid
    )
    # A claim owned by a different user.
    foreign_analysis = Analysis(
        input_type=AnalysisInputType.TEXT, user_id=uuid4(), content="x"
    )
    claims_service.save_from_analysis(
        foreign_analysis,
        ClaimAnalysis(
            claims=[ClaimItem(text="foreign", verifiability=0.5)],
            summary="s",
            model="mock",
        ),
    )
    foreign = claims_service._repository.list_by_analysis(
        foreign_analysis.analysis_id
    )[0]

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/claims/{foreign.id}", headers=_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "claim.not_found"


def test_get_claim_requires_token(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """Claims are owner-scoped and require a bearer token."""
    app, _ = _build(settings, token_verifier, user_service, owner_id=verified_identity.uid)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/claims/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_get_missing_claim_is_404(
    settings, token_verifier, user_service, verified_identity
) -> None:
    """An unknown claim id yields a 404 envelope."""
    app, _ = _build(settings, token_verifier, user_service, owner_id=verified_identity.uid)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/claims/{uuid4()}", headers=_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "claim.not_found"


def test_claims_not_configured_returns_503(authed_client: TestClient) -> None:
    """Without a wired claims service, the endpoint answers 503."""
    response = authed_client.get(f"/api/v1/claims/{uuid4()}", headers=_headers())
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "claims.not_configured"
