"""ERC-8004 passport router — reads agent passports off Arc."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException

from pantheon_api.deps import UserDep

router = APIRouter()


@router.get("/")
async def list_passports(user: UserDep) -> dict:
    # Off-chain enumeration of every agent passport requires a subgraph;
    # surface the council names + registry address so the dashboard can
    # fan out into per-agent lookups.
    from pantheon_api.routers.agents import COUNCIL

    return {
        "registry_address": os.environ.get("ERC8004_REGISTRY_ADDRESS", ""),
        "agents": [a["name"] for a in COUNCIL],
    }


@router.get("/{agent}")
async def get_passport(agent: str, user: UserDep) -> dict:
    if not os.environ.get("ERC8004_REGISTRY_ADDRESS"):
        raise HTTPException(
            status_code=503,
            detail="ERC8004_REGISTRY_ADDRESS not configured",
        )
    try:
        from parthenon.erc8004_client import Erc8004Client
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"erc8004 client missing: {e}")
    try:
        return await Erc8004Client().get(agent)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"on-chain read failed: {e}")
