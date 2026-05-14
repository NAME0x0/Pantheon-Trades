"""Counterfactual router — recent what-if simulation results."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def list_counterfactuals(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(20, ge=1, le=200),
) -> dict:
    raw_entries = await redis.xrevrange("elysium:counterfactuals", count=limit)
    items: list[dict] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if payload:
            try:
                items.append(json.loads(payload))
            except (ValueError, json.JSONDecodeError):
                pass
    return {"items": items, "count": len(items)}
