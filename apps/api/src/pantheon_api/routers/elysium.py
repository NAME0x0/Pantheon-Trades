"""Elysium router — last backtest result + paper-arena leaderboard."""

from __future__ import annotations

import json

from fastapi import APIRouter

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/last")
async def last_backtest(redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get("elysium:last_backtest")
    if not raw:
        return {"summary": {}, "trades": []}
    return json.loads(raw)


@router.get("/arena")
async def arena_leaderboard(redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get("elysium:arena_leaderboard")
    if not raw:
        return {"entries": []}
    return json.loads(raw)
