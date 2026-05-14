"""Public entry point for Boule: deliberate(signal) -> Thesis."""

from __future__ import annotations

import os
import uuid

import anthropic
import redis.asyncio as aioredis

from pantheon_core.schema import Signal, Thesis

from boule.debate import run_debate
from boule.trace import Tracer


async def deliberate(
    signal: Signal,
    *,
    redis_url: str | None = None,
    anthropic_client: anthropic.AsyncAnthropic | None = None,
    redis_client: aioredis.Redis | None = None,
) -> Thesis:
    """Run a single deliberation for the given signal.

    Both `anthropic_client` and `redis_client` are accepted so tests can inject
    fakes; production code paths pass nothing and we build clients from env.
    """
    close_anthropic = False
    close_redis = False

    if anthropic_client is None:
        api_key = os.environ["ANTHROPIC_API_KEY"]
        anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
        close_anthropic = True

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
            signal=signal, client=anthropic_client, tracer=tracer, thesis_id=thesis_id
        )
    finally:
        if close_redis:
            await redis_client.aclose()
        if close_anthropic:
            await anthropic_client.close()
