"""Per-address request rate limiting backed by Redis INCR + TTL."""

from __future__ import annotations

import redis.asyncio as aioredis

WINDOW_SECONDS = 60
DEFAULT_LIMIT = 60


async def check_rate_limit(
    redis: aioredis.Redis,
    bucket: str,
    *,
    limit: int = DEFAULT_LIMIT,
    window_seconds: int = WINDOW_SECONDS,
) -> tuple[bool, int]:
    """Returns ``(allowed, current_count)`` for the bucket."""
    key = f"rl:{bucket}:{window_seconds}"
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    count = int(results[0])
    return count <= limit, count
