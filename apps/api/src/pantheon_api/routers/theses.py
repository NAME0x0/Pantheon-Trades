"""Theses router — most-recent thesis decisions from Boule."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()

STREAM = "boule:theses"


@router.get("/")
async def list_theses(
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


@router.get("/{thesis_id}")
async def get_thesis(thesis_id: str, redis: RedisDep, user: UserDep) -> dict:
    cached = await redis.get(f"boule:thesis:{thesis_id}")
    if cached:
        return json.loads(cached)
    return {"error": "not_found", "thesis_id": thesis_id}
