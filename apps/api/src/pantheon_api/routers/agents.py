"""Agents router — council roster + per-agent credibility weights."""

from __future__ import annotations

import json

from fastapi import APIRouter

from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()

COUNCIL = (
    {"name": "ares",       "role": "bull advocate",       "weight": 1.0, "veto": False},
    {"name": "hades",      "role": "risk sovereign",      "weight": 2.0, "veto": False},
    {"name": "athena",     "role": "synthesist",          "weight": 1.5, "veto": False},
    {"name": "cassandra",  "role": "tail-risk prophet",   "weight": 1.0, "veto": False},
    {"name": "solon",      "role": "lawgiver",            "weight": 1.0, "veto": True},
    {"name": "zeus",       "role": "constitutional",      "weight": 1.0, "veto": True},
    {"name": "themis",     "role": "proportionality",     "weight": 1.0, "veto": False},
    {"name": "hephaestus", "role": "execution",           "weight": 1.0, "veto": False},
    {"name": "daedalus",   "role": "structure",           "weight": 1.0, "veto": False},
    {"name": "humans",     "role": "oversight",           "weight": 1.0, "veto": False},
)


@router.get("/")
async def list_agents(redis: RedisDep, user: UserDep) -> dict:
    items = []
    for agent in COUNCIL:
        weight = await redis.get(f"ostrakon:weights:{agent['name']}")
        state_raw = await redis.get(f"ostrakon:state:{agent['name']}")
        state = json.loads(state_raw) if state_raw else {}
        items.append(
            {
                **agent,
                "credibility_weight": float(weight) if weight else agent["weight"],
                "prediction_count": len(state.get("predictions", [])),
            }
        )
    return {"items": items, "count": len(items)}


@router.get("/{agent}")
async def get_agent(agent: str, redis: RedisDep, user: UserDep) -> dict:
    entry = next((a for a in COUNCIL if a["name"] == agent.lower()), None)
    if entry is None:
        return {"error": "not_found", "agent": agent}
    weight = await redis.get(f"ostrakon:weights:{agent.lower()}")
    state_raw = await redis.get(f"ostrakon:state:{agent.lower()}")
    state = json.loads(state_raw) if state_raw else {}
    return {
        **entry,
        "credibility_weight": float(weight) if weight else entry["weight"],
        "prediction_count": len(state.get("predictions", [])),
        "recent_returns": state.get("returns", [])[-10:],
    }
