"""Public entry point for Boule: deliberate(signal) -> Thesis."""

from __future__ import annotations

import os
import uuid

import redis.asyncio as aioredis

from pantheon_core.schema import Signal, Thesis

from boule.debate import run_debate
from boule.llm import LLMClient, build_default_client
from boule.trace import Tracer


async def deliberate(
    signal: Signal,
    *,
    redis_url: str | None = None,
    llm_client: LLMClient | None = None,
    redis_client: aioredis.Redis | None = None,
    # Legacy alias kept so existing integration tests keep working.
    anthropic_client: LLMClient | None = None,
) -> Thesis:
    """Run a single deliberation for the given signal.

    ``llm_client`` and ``redis_client`` are accepted so tests can inject
    fakes; production code paths pass nothing and we build clients from
    env. ``anthropic_client`` is a backwards-compatible alias for
    ``llm_client``.
    """
    close_llm = False
    close_redis = False
    client = llm_client or anthropic_client

    if client is None:
        client = build_default_client()
        close_llm = True

    if redis_client is None:
        url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await aioredis.from_url(url)
        close_redis = True

    thesis_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    tracer = Tracer(
        redis_client=redis_client,
        trace_id=trace_id,
        thesis_id=thesis_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
    )

    try:
        return await run_debate(
            signal=signal, client=client, tracer=tracer, thesis_id=thesis_id
        )
    finally:
        if close_redis:
            await redis_client.aclose()
        if close_llm:
            await client.close()
