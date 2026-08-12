"""Unit tests for the Phase 7 rate-limiting primitives."""

from __future__ import annotations

import pytest
import redis
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.infrastructure.rate_limit.factory import build_rate_limiter
from app.infrastructure.rate_limit.limiter import (
    FixedWindowRateLimiter,
    NoopRateLimiter,
    RateLimit,
    parse_rate,
)
from app.infrastructure.rate_limit.store import (
    InMemoryRateLimitStore,
    RedisRateLimitStore,
)


class FakeClock:
    """Deterministic clock for window-boundary tests."""

    def __init__(self, now: float) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _limiter(
    default: str = "120/minute",
    analysis: str = "20/minute",
    now: float = 0.0,
) -> FixedWindowRateLimiter:
    return FixedWindowRateLimiter(
        InMemoryRateLimitStore(),
        parse_rate(default),
        parse_rate(analysis),
        clock=FakeClock(now),
    )


def test_parse_rate_accepts_documented_units() -> None:
    assert parse_rate("120/minute") == RateLimit(120, 60)
    assert parse_rate("10/second") == RateLimit(10, 1)
    assert parse_rate("1000/hour") == RateLimit(1000, 3600)
    assert parse_rate("2/day") == RateLimit(2, 86400)
    assert parse_rate(" 5/MINUTE ") == RateLimit(5, 60)  # whitespace + case


def test_parse_rate_rejects_garbage() -> None:
    for bad in ("", "abc", "10/fortnight", "0/minute", "-1/minute", "10"):
        with pytest.raises(ConfigurationError):
            parse_rate(bad)


def test_fixed_window_counts_per_client() -> None:
    limiter = _limiter(default="2/minute")
    assert limiter.allow("default", "alice") is True
    assert limiter.allow("default", "alice") is True
    assert limiter.allow("default", "alice") is False  # exceeded
    assert limiter.allow("default", "bob") is True  # fresh client


def test_fixed_window_rolls_over() -> None:
    clock = FakeClock(0.0)
    limiter = FixedWindowRateLimiter(
        InMemoryRateLimitStore(),
        parse_rate("1/minute"),
        parse_rate("1/minute"),
        clock=clock,
    )
    assert limiter.allow("default", "alice") is True
    assert limiter.allow("default", "alice") is False
    clock.now = 60.0  # next window
    assert limiter.allow("default", "alice") is True


def test_analysis_scope_has_its_own_limit() -> None:
    limiter = _limiter(default="100/minute", analysis="1/minute")
    assert limiter.allow("analysis", "alice") is True
    assert limiter.allow("analysis", "alice") is False  # analysis quota spent
    assert limiter.allow("default", "alice") is True  # default quota untouched


def test_unknown_scope_falls_back_to_default() -> None:
    limiter = _limiter(default="1/minute")
    assert limiter.allow("other", "alice") is True
    assert limiter.allow("other", "alice") is False


def test_noop_limiter_always_allows() -> None:
    noop = NoopRateLimiter()
    for _ in range(1000):
        assert noop.allow("default", "alice") is True


class StubPipeline:
    """Records the INCR + EXPIRE-NX sequence a real Redis pipeline would run."""

    def __init__(self) -> None:
        self.incr_keys: list[str] = []
        self.expires: list[tuple[str, int]] = []

    def incr(self, key: str) -> StubPipeline:
        self.incr_keys.append(key)
        return self

    def expire(self, key: str, ttl: int, nx: bool = False) -> StubPipeline:
        self.expires.append((key, ttl))
        return self

    def execute(self) -> list[object]:
        return [5, True]


class StubRedisClient:
    def __init__(self) -> None:
        self.pipelines: list[StubPipeline] = []

    def pipeline(self) -> StubPipeline:
        pipeline = StubPipeline()
        self.pipelines.append(pipeline)
        return pipeline


def test_redis_store_increments_with_ttl_only_on_first() -> None:
    client = StubRedisClient()
    store = RedisRateLimitStore(client)  # type: ignore[arg-type]
    assert store.increment_and_get("rl:x", 60) == 5
    pipeline = client.pipelines[0]
    assert pipeline.incr_keys == ["rl:x"]
    assert pipeline.expires == [("rl:x", 60)]


def test_factory_returns_noop_without_redis(settings: Settings, caplog) -> None:
    limiter = build_rate_limiter(settings)
    assert isinstance(limiter, NoopRateLimiter)
    assert limiter.allow("default", "x") is True
    assert "rate limiting is disabled" in caplog.text


def test_factory_builds_redis_backed_limiter() -> None:
    settings = Settings(_env_file=None, redis_url="redis://localhost:6379/0")
    # Constructing a client does not connect; the factory only wires it in.
    client = redis.Redis.from_url("redis://localhost:6379/0")
    limiter = build_rate_limiter(settings, client)
    assert isinstance(limiter, FixedWindowRateLimiter)
