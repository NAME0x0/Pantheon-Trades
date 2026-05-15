"""Watchdog tick — check heartbeats + trigger pause if too many fail."""

from __future__ import annotations


import redis.asyncio as aioredis

from pantheon_api.healing.health import service_health
from pantheon_api.healing.pause import pause_system

CRITICAL_FAILURE_THRESHOLD = 2


async def watchdog_tick(redis: aioredis.Redis) -> dict:
    reports = await service_health(redis)
    failing = [r for r in reports if not r.healthy]
    summary = {
        "checked": len(reports),
        "failing": [r.name for r in failing],
    }
    if len(failing) >= CRITICAL_FAILURE_THRESHOLD:
        paused = await pause_system(
            redis, reason=f"watchdog: {len(failing)} services unhealthy"
        )
        summary["action"] = "paused"
        summary["state"] = paused
    return summary
