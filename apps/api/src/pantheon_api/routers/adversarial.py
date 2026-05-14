"""Adversarial mode router — toggle Boule's bear-stress mode."""

from __future__ import annotations

import json

from fastapi import APIRouter

from pantheon_api.auth.rbac import require_admin
from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


@router.get("/")
async def adversarial_state(redis: RedisDep, user: UserDep) -> dict:
    raw = await redis.get("olympus:adversarial")
    if not raw:
        return {"enabled": False, "bear_weight_multiplier": 2.0, "require_super_majority": True}
    return json.loads(raw)


@router.post("/enable")
async def enable(redis: RedisDep, user: UserDep) -> dict:
    require_admin(user)
    state = {"enabled": True, "bear_weight_multiplier": 2.0, "require_super_majority": True}
    await redis.set("olympus:adversarial", json.dumps(state))
    return state


@router.post("/disable")
async def disable(redis: RedisDep, user: UserDep) -> dict:
    require_admin(user)
    state = {"enabled": False, "bear_weight_multiplier": 2.0, "require_super_majority": True}
    await redis.set("olympus:adversarial", json.dumps(state))
    return state
