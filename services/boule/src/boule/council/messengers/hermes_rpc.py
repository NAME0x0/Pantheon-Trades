"""Hermes RPC client — read-only Arc Testnet probes."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class RpcClient:
    http: httpx.AsyncClient
    rpc_url: str = os.environ.get("RPC_URL", "https://rpc.testnet.arc.network")

    async def _call(self, method: str, params: list | None = None) -> dict:
        r = await self.http.post(
            self.rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
        )
        r.raise_for_status()
        return r.json()

    async def chain_id(self) -> int:
        return int((await self._call("eth_chainId"))["result"], 16)

    async def block_number(self) -> int:
        return int((await self._call("eth_blockNumber"))["result"], 16)

    async def gas_price(self) -> int:
        return int((await self._call("eth_gasPrice"))["result"], 16)
