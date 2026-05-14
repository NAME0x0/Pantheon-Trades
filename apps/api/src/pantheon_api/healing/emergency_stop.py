"""Emergency stop — flips Olympus to PAUSED and refuses new trades."""

from __future__ import annotations

import json

import redis.asyncio as aioredis


async def emergency_stop(redis: aioredis.Redis, reason: str) -> dict:
    payload = {"state": "paused", "reason": f"emergency: {reason}"}
    await redis.set("olympus:state", json.dumps(payload))
    return payload
