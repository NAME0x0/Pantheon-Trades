"""Markets router — proxies Polymarket CLOB for active markets."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query

from pantheon_api.deps import UserDep

router = APIRouter()

POLYMARKET_HOST = "https://clob.polymarket.com"


@router.get("/")
async def list_markets(
    user: UserDep,
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{POLYMARKET_HOST}/markets", params={"limit": limit})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"polymarket fetch failed: {e}")
        payload = resp.json()
    markets = payload.get("data") if isinstance(payload, dict) else payload
    return {"items": markets or [], "count": len(markets or [])}


@router.get("/{market_id}")
async def get_market(market_id: str, user: UserDep) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{POLYMARKET_HOST}/markets/{market_id}")
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"polymarket fetch failed: {e}")
        return resp.json()
