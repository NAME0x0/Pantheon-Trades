"""Argos heartbeat — periodic liveness ping for Olympus to consume."""

from __future__ import annotations

import asyncio

import structlog
from redis.asyncio import Redis

from pantheon_core.schema import utc_now

log = structlog.get_logger("argos.heartbeat")

HEARTBEAT_KEY = "argos:heartbeat"


async def write_heartbeat(redis: Redis, *, ttl_seconds: int = 60) -> None:
    payload = {"ts": utc_now().isoformat()}
    try:
        await redis.setex(HEARTBEAT_KEY, ttl_seconds, str(payload))
    except Exception as e:
        log.warning("argos.heartbeat_failed", error=str(e))


async def run_heartbeat(redis: Redis, *, interval_seconds: float = 15.0) -> None:
    while True:
        await write_heartbeat(redis)
        await asyncio.sleep(interval_seconds)
