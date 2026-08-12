"""API tests for the v1 analysis endpoints."""

import base64
from uuid import UUID, uuid4

from app.application.ports.ai import AnalysisProviderError
from app.application.ports.media import (
    FetchedPage,
    MediaProcessingError,
    UrlFetchError,
)
from app.application.services.analysis_service import AnalysisService
from app.application.services.media_pipeline import MediaPipeline
from app.core.config import Settings
from app.domain.analysis import AnalysisStatus
from app.infrastructure.media.mock_media_adapters import (
    MockForensicsAdapter,
    MockOcrAdapter,
)
from app.infrastructure.repositories.mock_analysis_repository import (
    MockAnalysisRepository,
)
from app.main import create_app
from fastapi.testclient import TestClient


class FakeUrlFetcher:
    """Deterministic fetcher for the media-wired test service."""

    def __init__(
        self,
        page: FetchedPage | None = None,
        error: Exception | None = None,
    ) -> None:
        self.page = page or FetchedPage(
            final_url="https://example.com/final",
            status=200,
            text="page text",
        )
        self.error = error

    def fetch(
        self,
        url: str,
        *,
        timeout: float = 10.0,
        max_bytes: int = 2_000_000,
    ) -> FetchedPage:
        if self.error is not None:
            raise self.error
        return self.page


def _media_service(*, fetcher_error: Exception | None = None) -> AnalysisService:
    """An analysis service wired with a media pipeline of deterministic fakes."""
    return AnalysisService(
        MockAnalysisRepository(),
        media_pipeline=MediaPipeline(
            url_fetcher=FakeUrlFetcher(error=fetcher_error),
            ocr_adapter=MockOcrAdapter(),
            forensics_adapter=MockForensicsAdapter(),
        ),
    )


def _headers() -> dict[str, str]:
    """Headers authenticating as the fixed test identity."""
    return {"Authorization": "Bearer test-token"}


def _submit(client: TestClient, text: str = "The sky is blue.") -> dict:
    """Submit a text analysis as the test identity and return its payload."""
    response = client.post("/api/v1/analysis", json={"text": text}, headers=_headers())
    assert response.status_code == 202
    return response.json()["data"]


def test_submit_text_returns_202_with_report(authed_client: TestClient) -> None:
    """A text submission completes and returns the persisted report."""
    data = _submit(authed_client)
    assert data["status"] == "completed"
    assert data["input_type"] == "text"
    assert data["report"]["summary"] == "mock summary"
    # Phase 14: claims carry a verdict, rationale, and evidence.
    assert data["report"]["claims"] == [
        {
            "text": "mock claim",
            "verifiability": 0.5,
            "verdict": "partially_verifiable",
            "rationale": "Mock analyzer: verifiability 0.50 is mid-range.",
            "evidence": [
                {
                    "kind": "link",
                    "url": "https://example.com/evidence",
                    "quote": None,
                    "snippet": None,
                    "relevance": 0.5,
                }
            ],
        }
    ]
    assert data["completed_at"] is not None


def test_submit_anonymous_allowed(authed_client: TestClient, analysis_service) -> None:
    """Anonymous submissions carry no owner and still complete."""
    response = authed_client.post("/api/v1/analysis", json={"text": "hello"})
    assert response.status_code == 202
    analysis_id = UUID(response.json()["data"]["id"])
    fetched = analysis_service.get(analysis_id)
    assert fetched is not None
    assert fetched.user_id is None
    assert fetched.status.value == "completed"


def test_submit_image_requires_image_payload(authed_client: TestClient) -> None:
    """An image submission without the image payload is a validation error."""
    response = authed_client.post(
        "/api/v1/analysis", json={"input_type": "image", "text": "x"}, headers=_headers()
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_image"


def test_submit_url_completes_with_media_context(
    settings: Settings, token_verifier, user_service
) -> None:
    """A URL submission is fetched and the report carries the media context."""
    service = _media_service()
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=service,
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/api/v1/analysis",
            json={"input_type": "url", "url": "https://example.com/article"},
            headers=_headers(),
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "completed"
    assert data["input_type"] == "url"
    media = data["report"]["media"]
    assert media["input"]["type"] == "url"
    assert media["input"]["url"] == "https://example.com/article"
    assert media["input"]["final_url"] == "https://example.com/final"
    assert media["input"]["status"] == 200
    assert data["report"]["summary"] == "mock summary"


def test_submit_image_completes_with_ocr_and_forensics(
    settings: Settings, token_verifier, user_service
) -> None:
    """An image submission runs OCR + forensics and reports their output."""
    service = _media_service()
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=service,
    )
    image = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/api/v1/analysis",
            json={"input_type": "image", "image": image},
            headers=_headers(),
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "completed"
    media = data["report"]["media"]
    assert media["input"]["type"] == "image"
    assert media["input"]["mime"] == "image/png"
    assert media["ocr"]["text"] == "mock ocr text"
    assert media["forensics"]["risk_score"] == 0.0


def test_submit_rejects_malformed_image(authed_client: TestClient) -> None:
    """Base64 garbage is rejected at the API boundary with a clear error."""
    response = authed_client.post(
        "/api/v1/analysis",
        json={"input_type": "image", "image": "!!!not-base64!!!"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_image"


def test_submit_rejects_oversized_image(
    settings: Settings, token_verifier, user_service
) -> None:
    """Images above the configured byte cap are rejected with a clear error."""
    capped_settings = Settings(
        _env_file=None, app_env="test", media_image_max_bytes=10
    )
    service = _media_service()
    app = create_app(
        capped_settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=service,
    )
    image = base64.b64encode(b"x" * 64).decode()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/api/v1/analysis",
            json={"input_type": "image", "image": image},
            headers=_headers(),
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_image"


def test_submit_rejects_non_http_url(authed_client: TestClient) -> None:
    """Non-http(s) URLs are refused at the API boundary."""
    response = authed_client.post(
        "/api/v1/analysis",
        json={"input_type": "url", "url": "ftp://example.com/file"},
        headers=_headers(),
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_url"


def test_submit_unfetchable_url_fails_cleanly(
    settings: Settings, token_verifier, user_service
) -> None:
    """An SSRF-refused URL surfaces as a FAILED analysis, not a 500."""
    service = _media_service(fetcher_error=UrlFetchError("refused by the SSRF guard"))
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=service,
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/api/v1/analysis",
            json={"input_type": "url", "url": "http://192.168.1.1/"},
            headers=_headers(),
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "failed"
    assert data["failure_reason"] == "analysis.fetch_failed"


def test_submit_undecodable_image_fails_cleanly(
    settings: Settings, token_verifier, user_service
) -> None:
    """A media-processing failure surfaces as a FAILED analysis, not a 500."""

    class BrokenOcr:
        def extract_text(self, image_bytes: bytes):
            raise MediaProcessingError("cannot decode image")

    service = AnalysisService(
        MockAnalysisRepository(),
        media_pipeline=MediaPipeline(
            url_fetcher=FakeUrlFetcher(),
            ocr_adapter=BrokenOcr(),  # type: ignore[arg-type]
            forensics_adapter=MockForensicsAdapter(),
        ),
    )
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=service,
    )
    image = base64.b64encode(b"fake-image").decode()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/api/v1/analysis",
            json={"input_type": "image", "image": image},
            headers=_headers(),
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "failed"
    assert data["failure_reason"] == "analysis.media_failed"


def test_submit_failed_when_provider_errors(
    settings: Settings, token_verifier, user_service, analysis_service
) -> None:
    """A provider failure surfaces as a FAILED analysis, not a 500."""

    class FailingAnalyzer:
        def analyze(self, text: str):
            raise AnalysisProviderError("provider down")

    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=analysis_service,
        claim_analyzer=FailingAnalyzer(),  # type: ignore[arg-type]
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post("/api/v1/analysis", json={"text": "x"}, headers=_headers())
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "failed"
    assert data["failure_reason"] == "analysis.processing_failed"


def test_get_returns_owned_analysis(authed_client: TestClient) -> None:
    """The owner can fetch the analysis with its report."""
    created = _submit(authed_client)
    response = authed_client.get(f"/api/v1/analysis/{created['id']}", headers=_headers())
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == created["id"]
    assert data["report"] == created["report"]


def test_get_hides_anonymous_analyses_from_users(authed_client: TestClient) -> None:
    """Anonymous rows (no owner) are never exposed to authenticated users."""
    created = authed_client.post("/api/v1/analysis", json={"text": "anonymous"}).json()["data"]
    assert created["status"] == "completed"
    response = authed_client.get(f"/api/v1/analysis/{created['id']}", headers=_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis.not_found"


def test_get_missing_returns_404(authed_client: TestClient) -> None:
    """An unknown analysis ID yields a 404 envelope."""
    response = authed_client.get(f"/api/v1/analysis/{uuid4()}", headers=_headers())
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis.not_found"


def test_get_requires_token(authed_client: TestClient) -> None:
    """Reading an analysis requires a bearer token."""
    response = authed_client.get(f"/api/v1/analysis/{uuid4()}")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth.missing_token"


def test_list_returns_own_analyses_newest_first(authed_client: TestClient) -> None:
    """Listing returns only the caller's analyses."""
    first = _submit(authed_client)
    second = _submit(authed_client)
    # An anonymous row must not leak into an authenticated listing.
    authed_client.post("/api/v1/analysis", json={"text": "anonymous"})

    response = authed_client.get("/api/v1/analysis", headers=_headers())
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == [second["id"], first["id"]]


def test_list_paginates_with_cursor(authed_client: TestClient) -> None:
    """Cursor pagination walks all pages without duplication."""
    for _ in range(3):
        _submit(authed_client)

    page_one = authed_client.get(
        "/api/v1/analysis", params={"limit": 2}, headers=_headers()
    ).json()
    assert len(page_one["data"]) == 2
    next_cursor = page_one["meta"]["next_cursor"]
    assert next_cursor is not None

    page_two = authed_client.get(
        "/api/v1/analysis", params={"limit": 2, "cursor": next_cursor}, headers=_headers()
    ).json()
    assert len(page_two["data"]) == 1
    assert page_two["meta"]["next_cursor"] is None


def test_list_rejects_malformed_cursor(authed_client: TestClient) -> None:
    """A garbled cursor yields a validation error envelope."""
    response = authed_client.get(
        "/api/v1/analysis", params={"cursor": "!!!not-a-cursor!!!"}, headers=_headers()
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation.invalid_cursor"


def test_delete_removes_owned_analysis(authed_client: TestClient) -> None:
    """The owner can delete an analysis; it disappears afterwards."""
    created = _submit(authed_client)
    response = authed_client.delete(f"/api/v1/analysis/{created['id']}", headers=_headers())
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] == created["id"]

    gone = authed_client.get(f"/api/v1/analysis/{created['id']}", headers=_headers())
    assert gone.status_code == 404


def test_analysis_not_configured_returns_503(client: TestClient) -> None:
    """Without a wired analysis service, the endpoint answers 503."""
    response = client.post("/api/v1/analysis", json={"text": "x"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "analysis.not_configured"


def test_submit_enqueues_when_worker_configured(
    settings: Settings, token_verifier, user_service
) -> None:
    """With a dispatcher bound, POST returns PENDING + retry_after and enqueues."""

    class FakeDispatcher:
        def __init__(self) -> None:
            self.dispatched: list[UUID] = []

        def dispatch(self, analysis_id: UUID) -> None:
            self.dispatched.append(analysis_id)

    dispatcher = FakeDispatcher()
    repository = MockAnalysisRepository()
    service = AnalysisService(repository, task_dispatcher=dispatcher)
    app = create_app(
        settings,
        token_verifier=token_verifier,
        user_service=user_service,
        analysis_service=service,
    )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            "/api/v1/analysis", json={"text": "hello"}, headers=_headers()
        )

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert response.json()["meta"]["retry_after"] == 5
    analysis_id = UUID(data["id"])
    assert dispatcher.dispatched == [analysis_id]
    # The row persists in PENDING; the worker would complete it asynchronously.
    assert repository.get(analysis_id).status is AnalysisStatus.PENDING
