from __future__ import annotations

import json

import redis.asyncio as aioredis

TTL_SECONDS = 60


class SignalCache:
    """Redis-backed cache for market snapshots and signals."""

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def set_snapshot(self, market_id: str, data: dict, ttl: int = TTL_SECONDS) -> None:
        key = f"pythia:snapshot:{market_id}"
        await self._redis.setex(key, ttl, json.dumps(data))

    async def get_snapshot(self, market_id: str) -> dict | None:
        key = f"pythia:snapshot:{market_id}"
        raw = await self._redis.get(key)
        return json.loads(raw) if raw else None

    async def staleness_seconds(self, market_id: str) -> int:
        key = f"pythia:snapshot:{market_id}"
        ttl = await self._redis.ttl(key)
        if ttl < 0:
            return 999999
        return max(0, TTL_SECONDS - ttl)
