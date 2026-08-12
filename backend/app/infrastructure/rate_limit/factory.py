"""Composition-root factory for the rate limiter (Phase 7)."""

from __future__ import annotations

import logging

import redis

from app.core.config import Settings
from app.infrastructure.rate_limit.limiter import (
    FixedWindowRateLimiter,
    NoopRateLimiter,
    RateLimiter,
    parse_rate,
)
from app.infrastructure.rate_limit.store import RedisRateLimitStore

logger = logging.getLogger(__name__)


def build_rate_limiter(
    settings: Settings, redis_client: redis.Redis | None = None
) -> RateLimiter:
    """Build the configured rate limiter.

    When Redis is configured the limiter is backed by it; otherwise a
    permissive no-op is returned with a logged warning so development and
    tests never require a broker (mirrors the OCR mock fallback).
    """
    if redis_client is None:
        logger.warning(
            "REDIS_URL is not set — rate limiting is disabled (no-op limiter)"
        )
        return NoopRateLimiter()
    return FixedWindowRateLimiter(
        RedisRateLimitStore(redis_client),
        default_limit=parse_rate(settings.rate_limit_default),
        analysis_limit=parse_rate(settings.rate_limit_analysis),
    )
