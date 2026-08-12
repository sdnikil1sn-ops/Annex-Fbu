"""API tests for the Phase 7 rate-limit middleware."""

from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.rate_limit.limiter import FixedWindowRateLimiter, RateLimit
from app.infrastructure.rate_limit.store import InMemoryRateLimitStore
from app.main import create_app
from fastapi.testclient import TestClient


class FakeClock:
    """Deterministic clock pinned inside one fixed window."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _app(default: RateLimit, analysis: RateLimit, now: float = 0.0):
    settings = Settings(_env_file=None, app_env="test", log_level="WARNING")
    limiter = FixedWindowRateLimiter(
        InMemoryRateLimitStore(),
        default,
        analysis,
        clock=FakeClock(now),
    )
    return create_app(settings, rate_limiter=limiter)


def test_default_scope_429_after_limit() -> None:
    app = _app(RateLimit(2, 60), RateLimit(100, 60))
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
        limited = client.get("/health")
        assert limited.status_code == 429
        error = limited.json()["error"]
        assert error["code"] == "rate_limit.exceeded"
        assert error["details"]["scope"] == "default"
        assert error["request_id"] is not None


def test_analysis_scope_limited_independently() -> None:
    app = _app(RateLimit(100, 60), RateLimit(1, 60))
    with TestClient(app, raise_server_exceptions=False) as client:
        # Limiting runs before route handling: the first analysis request is
        # counted (503 here — no service configured — but still counted)...
        assert client.post("/api/v1/analysis", json={"text": "x"}).status_code == 503
        # ...and the second is rejected before it reaches the route.
        assert (
            client.post("/api/v1/analysis", json={"text": "x"}).status_code == 429
        )
        # ...while the default scope is unaffected.
        assert client.get("/health").status_code == 200


def test_window_rollover_resets_limit() -> None:
    clock = FakeClock(0.0)
    settings = Settings(_env_file=None, app_env="test", log_level="WARNING")
    limiter = FixedWindowRateLimiter(
        InMemoryRateLimitStore(),
        RateLimit(1, 60),
        RateLimit(1, 60),
        clock=clock,
    )
    app = create_app(settings, rate_limiter=limiter)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 429
        clock.now = 60.0
        assert client.get("/health").status_code == 200
