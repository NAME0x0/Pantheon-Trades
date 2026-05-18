from __future__ import annotations

import os

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

# Honours POLYMARKET_CLOB env so an operator behind a geo-block can
# point us at a Vercel edge proxy (see apps/web/app/api/polymarket-proxy/).
CLOB_API = os.environ.get("POLYMARKET_CLOB", "https://clob.polymarket.com")


class PolymarketSource(DataSource):
    name = "polymarket"
    max_staleness_seconds = 60

    async def fetch(self) -> SourceSnapshot:
        resp = await self._client.get(f"{CLOB_API}/markets", timeout=10.0)
        resp.raise_for_status()
        return SourceSnapshot(source=self.name, fetched_at=utc_now(), data={"markets": resp.json()})

    async def fetch_market(self, condition_id: str) -> dict:
        resp = await self._client.get(f"{CLOB_API}/markets/{condition_id}", timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def fetch_orderbook(self, token_id: str) -> dict:
        resp = await self._client.get(f"{CLOB_API}/book", params={"token_id": token_id}, timeout=10.0)
        resp.raise_for_status()
        return resp.json()

    async def fetch_mid_price(self, token_id: str) -> float:
        book = await self.fetch_orderbook(token_id)
        bids = book.get("bids", [])
        asks = book.get("asks", [])
        best_bid = float(bids[0]["price"]) if bids else 0.0
        best_ask = float(asks[0]["price"]) if asks else 1.0
        return (best_bid + best_ask) / 2.0
