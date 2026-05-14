"""Underworld router — post-mortems for resolved trades."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def list_postmortems(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    raw_entries = await redis.xrevrange("underworld:postmortems", count=limit)
    items: list[dict] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if payload:
            try:
                items.append(json.loads(payload))
            except (ValueError, json.JSONDecodeError):
                pass
    return {"items": items, "count": len(items)}


@router.get("/{pm_id}")
async def get_postmortem(pm_id: str, redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get(f"underworld:postmortem:{pm_id}")
    if not raw:
        return {"error": "not_found", "pm_id": pm_id}
    return json.loads(raw)
