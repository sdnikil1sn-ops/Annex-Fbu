"""Integration tests: Phase 7 Redis-backed infrastructure against a real broker.

Gated on TEST_REDIS_URL; skipped unless a local Redis is reachable. Covers
the rate-limit counter store and end-to-end task enqueueing onto the
analysis queue (ADR-0008).
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
import redis
from app.core.config import Settings
from app.infrastructure.rate_limit.store import RedisRateLimitStore
from app.infrastructure.tasks.celery_app import create_celery_app
from app.infrastructure.tasks.dispatcher import CeleryAnalysisTaskDispatcher

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_REDIS_URL, reason="TEST_REDIS_URL is not set"
)


def test_rate_limit_store_counts_across_windows() -> None:
    """INCR + EXPIRE-NX counters work against a real Redis server."""
    client = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    try:
        key = f"it:rate:{uuid4()}"
        store = RedisRateLimitStore(client)
        assert store.increment_and_get(key, 60) == 1
        assert store.increment_and_get(key, 60) == 2
        ttl = client.ttl(key)
        assert ttl > 0  # TTL set by the first increment
        client.delete(key)
    finally:
        client.close()


def test_dispatcher_enqueues_onto_analysis_queue() -> None:
    """Dispatch publishes the task message to the routed analysis queue."""
    settings = Settings(
        _env_file=None,
        redis_url=TEST_REDIS_URL,
        celery_broker_url=TEST_REDIS_URL,
        celery_result_backend=TEST_REDIS_URL,
    )
    app = create_celery_app(settings)
    dispatcher = CeleryAnalysisTaskDispatcher(app)

    analysis_id = uuid4()
    dispatcher.dispatch(analysis_id)

    client = redis.Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    try:
        # No worker is running here; the message waits in the queue. The
        # task ID equals the analysis ID (broker-level idempotency).
        size = client.llen("analysis")
        assert size >= 1
        client.lpop("analysis")
    finally:
        client.close()
