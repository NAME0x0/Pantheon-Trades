"""Trades router — most-recent paper/live trades from Redis stream."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()

STREAM = "strategos:trades"


@router.get("/")
async def list_trades(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    raw_entries = await redis.xrevrange(STREAM, count=limit)
    items: list[dict] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if payload:
            try:
                items.append(json.loads(payload))
            except (ValueError, json.JSONDecodeError):
                pass
    return {"items": items, "count": len(items)}


@router.get("/{trade_id}")
async def get_trade(trade_id: str, redis: RedisDep, user: UserDep) -> dict:
    cached = await redis.get(f"strategos:trade:{trade_id}")
    if cached:
        return json.loads(cached)
    return {"error": "not_found", "trade_id": trade_id}
