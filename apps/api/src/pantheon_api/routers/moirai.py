"""Moirai router — strategy lifecycle snapshots from Redis."""

from __future__ import annotations

import json

from fastapi import APIRouter

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def list_strategies(redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get("moirai:strategies")
    if not raw:
        return {"items": [], "count": 0}
    try:
        items = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return {"items": [], "count": 0}
    return {"items": items, "count": len(items)}


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str, redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get(f"moirai:strategy:{strategy_id}")
    if not raw:
        return {"error": "not_found", "strategy_id": strategy_id}
    return json.loads(raw)
