"""Traces router — replay of Boule deliberation events."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()

STREAM = "boule:traces"


@router.get("/")
async def list_traces(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(100, ge=1, le=1000),
    trace_id: str | None = Query(None),
) -> dict:
    raw_entries = await redis.xrevrange(STREAM, count=limit)
    items: list[dict] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if not payload:
            continue
        try:
            obj = json.loads(payload)
        except (ValueError, json.JSONDecodeError):
            continue
        if trace_id and obj.get("trace_id") != trace_id:
            continue
        items.append(obj)
    items.sort(key=lambda e: e.get("sequence", 0))
    return {"items": items, "count": len(items)}
