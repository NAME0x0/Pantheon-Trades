"""Signals router — recent Apollo signals from the Redis stream."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query


from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()

STREAM = "apollo:signals"


@router.get("/")
async def list_signals(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    raw_entries = await redis.xrevrange(STREAM, count=limit)
    items: list[dict] = []
    for entry_id, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if not payload:
            continue
        try:
            items.append(json.loads(payload))
        except (ValueError, json.JSONDecodeError):
            continue
    return {"items": items, "count": len(items)}


@router.get("/{signal_id}")
async def get_signal(signal_id: str, redis: RedisDep, user: UserDep) -> dict:
    cached = await redis.get(f"apollo:signal:{signal_id}")
    if cached:
        return json.loads(cached)
    # Fallback: scan recent stream entries.
    raw_entries = await redis.xrevrange(STREAM, count=500)
    for _entry_id, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if not payload:
            continue
        try:
            obj = json.loads(payload)
        except (ValueError, json.JSONDecodeError):
            continue
        if obj.get("signal_id") == signal_id:
            return obj
    return {"error": "not_found", "signal_id": signal_id}
