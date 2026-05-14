"""Feedback events — Boule publishes hits/misses so Ostrakon can score."""

from __future__ import annotations

import json

import redis.asyncio as aioredis

FEEDBACK_STREAM = "boule:feedback"


async def publish_feedback(
    redis: aioredis.Redis,
    *,
    thesis_id: str,
    agent: str,
    probability: float,
    actual_outcome: int,
    trade_return: float | None = None,
) -> None:
    payload = json.dumps(
        {
            "thesis_id": thesis_id,
            "agent": agent,
            "probability": probability,
            "actual_outcome": actual_outcome,
            "trade_return": trade_return,
        }
    )
    await redis.xadd(
        FEEDBACK_STREAM, {"data": payload}, maxlen=50_000, approximate=True
    )
