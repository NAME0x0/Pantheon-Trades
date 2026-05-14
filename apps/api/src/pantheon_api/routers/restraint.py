"""ProofOfRestraint router — reasons we declined to trade."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def list_restraint(
    redis: RedisDep,
    user: UserDep,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    raw_entries = await redis.xrevrange("areopagus:restraint", count=limit)
    items: list[dict] = []
    for _, fields in raw_entries:
        payload = fields.get("data") if isinstance(fields, dict) else None
        if payload:
            try:
                items.append(json.loads(payload))
            except (ValueError, json.JSONDecodeError):
                pass
    return {"items": items, "count": len(items)}
