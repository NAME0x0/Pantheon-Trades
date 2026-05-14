"""Debates router — full deliberation transcript grouped by trace_id."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/{trace_id}")
async def get_debate(
    trace_id: str,
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(500, ge=1, le=2000),
) -> dict:
    raw_entries = await redis.xrevrange("boule:traces", count=limit)
    events: list[dict] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if not payload:
            continue
        try:
            obj = json.loads(payload)
        except (ValueError, json.JSONDecodeError):
            continue
        if obj.get("trace_id") != trace_id:
            continue
        events.append(obj)
    events.sort(key=lambda e: e.get("sequence", 0))
    return {"trace_id": trace_id, "events": events, "count": len(events)}
