"""Credibility-weight reader — fetches Ostrakon weights from Redis.

Boule reads each agent's current credibility weight on startup so it can
amplify or attenuate per-agent vote influence in the next deliberation.
"""

from __future__ import annotations

import redis.asyncio as aioredis

WEIGHT_KEY_PREFIX = "ostrakon:weights"


async def fetch_agent_weight(
    redis: aioredis.Redis, agent: str, default: float = 1.0
) -> float:
    raw = await redis.get(f"{WEIGHT_KEY_PREFIX}:{agent}")
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


async def fetch_all_weights(
    redis: aioredis.Redis, agents: list[str]
) -> dict[str, float]:
    return {agent: await fetch_agent_weight(redis, agent) for agent in agents}
