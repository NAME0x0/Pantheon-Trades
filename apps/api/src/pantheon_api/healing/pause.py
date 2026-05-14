"""Pause / resume helpers — mirror the Olympus router moves into Redis."""

from __future__ import annotations

import json

import redis.asyncio as aioredis


async def pause_system(redis: aioredis.Redis, reason: str) -> dict:
    payload = {"state": "paused", "reason": reason}
    await redis.set("olympus:state", json.dumps(payload))
    return payload


async def resume_system(redis: aioredis.Redis) -> dict:
    payload = {"state": "recovery", "reason": "manual resume"}
    await redis.set("olympus:state", json.dumps(payload))
    return payload
