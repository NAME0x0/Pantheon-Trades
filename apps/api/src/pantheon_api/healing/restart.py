"""Restart request — publishes a control message; the orchestrator restarts."""

from __future__ import annotations

import json

import redis.asyncio as aioredis


CONTROL_STREAM = "olympus:control"


async def request_restart(redis: aioredis.Redis, service: str, reason: str = "") -> dict:
    payload = {"action": "restart", "service": service, "reason": reason}
    await redis.xadd(CONTROL_STREAM, {"data": json.dumps(payload)}, maxlen=1_000, approximate=True)
    return payload
