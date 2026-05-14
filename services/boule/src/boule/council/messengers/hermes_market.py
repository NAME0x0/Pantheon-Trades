"""Hermes market client — Polymarket CLOB read surface."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

POLYMARKET_HOST = "https://clob.polymarket.com"


@dataclass
class MarketClient:
    http: httpx.AsyncClient

    async def get_market(self, market_id: str) -> dict:
        r = await self.http.get(f"{POLYMARKET_HOST}/markets/{market_id}")
        r.raise_for_status()
        return r.json()

    async def get_book(self, token_id: str) -> dict:
        r = await self.http.get(f"{POLYMARKET_HOST}/book", params={"token_id": token_id})
        r.raise_for_status()
        return r.json()
