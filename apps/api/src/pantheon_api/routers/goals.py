"""Goals router — exposes Olympus goals board state from Redis."""

from __future__ import annotations

import json

from fastapi import APIRouter

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def list_goals(redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get("olympus:goals_board")
    if not raw:
        return {"items": [], "summary": {}}
    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return {"items": [], "summary": {}}
    return data
