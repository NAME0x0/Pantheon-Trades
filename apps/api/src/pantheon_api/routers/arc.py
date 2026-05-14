"""Arc Testnet status router — surfaces chain health to the dashboard."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException

from pantheon_api.config import settings
from pantheon_api.deps import UserDep

router = APIRouter()


@router.get("/status")
async def arc_status(user: UserDep) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            chain_id_resp = await client.post(
                settings.rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
            )
            chain_id_resp.raise_for_status()
            block_resp = await client.post(
                settings.rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 2},
            )
            block_resp.raise_for_status()
            gas_resp = await client.post(
                settings.rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_gasPrice", "params": [], "id": 3},
            )
            gas_resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"arc rpc failed: {e}")

    return {
        "rpc_url": settings.rpc_url,
        "expected_chain_id": settings.arc_chain_id,
        "chain_id": int(chain_id_resp.json()["result"], 16),
        "block_number": int(block_resp.json()["result"], 16),
        "gas_price_wei": int(gas_resp.json()["result"], 16),
        "registry_address": __import__("os").environ.get(
            "PARTHENON_REGISTRY_ADDRESS", ""
        ),
    }
