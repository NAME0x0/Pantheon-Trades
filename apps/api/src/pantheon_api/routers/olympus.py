"""Olympus router — system state + service health reports."""

from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from pantheon_api.auth.rbac import require_admin
from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


class PauseRequest(BaseModel):
    reason: str


@router.get("/")
async def olympus_state(redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get("olympus:state")
    services_raw = await redis.get("olympus:services")
    state = json.loads(raw) if raw else {"state": "standby"}
    services = json.loads(services_raw) if services_raw else {}
    return {"olympus": state, "services": services, "accepts_new_trades": state.get("state") == "active"}


@router.post("/pause")
async def pause(req: PauseRequest, redis: RedisDep, user: UserDep) -> dict:
    require_admin(user)
    payload = {"state": "paused", "reason": req.reason}
    await redis.set("olympus:state", json.dumps(payload))
    return payload


@router.post("/resume")
async def resume(redis: RedisDep, user: UserDep) -> dict:
    require_admin(user)
    payload = {"state": "recovery", "reason": "manual"}
    await redis.set("olympus:state", json.dumps(payload))
    return payload
