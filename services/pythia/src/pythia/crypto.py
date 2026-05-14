"""Crypto price oracle — CoinGecko public API.

We pull spot prices and 24h volume/volatility for a small whitelist of
assets relevant to Polymarket crypto markets (BTC, ETH, SOL, etc.). Public
endpoints have very strict rate limits, so all calls go through the shared
``RateLimiter`` and ``SignalCache`` to avoid bursts.
"""

from __future__ import annotations

import httpx

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

COINGECKO = "https://api.coingecko.com/api/v3"

SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "DOGE": "dogecoin",
    "MATIC": "matic-network",
    "ARB": "arbitrum",
    "OP": "optimism",
}


class CryptoSource(DataSource):
    name = "coingecko"
    max_staleness_seconds = 60

    def __init__(self, client: httpx.AsyncClient, symbols: list[str] | None = None) -> None:
        super().__init__(client)
        self._symbols = symbols or list(SYMBOL_TO_ID.keys())

    async def fetch(self) -> SourceSnapshot:
        ids = ",".join(SYMBOL_TO_ID[s] for s in self._symbols if s in SYMBOL_TO_ID)
        resp = await self._client.get(
            f"{COINGECKO}/simple/price",
            params={
                "ids": ids,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_24hr_change": "true",
                "include_last_updated_at": "true",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = {
            "prices": {
                sym: {
                    "usd": payload.get(SYMBOL_TO_ID[sym], {}).get("usd"),
                    "volume_24h": payload.get(SYMBOL_TO_ID[sym], {}).get("usd_24h_vol"),
                    "change_24h_pct": payload.get(SYMBOL_TO_ID[sym], {}).get("usd_24h_change"),
                    "updated_at": payload.get(SYMBOL_TO_ID[sym], {}).get("last_updated_at"),
                }
                for sym in self._symbols
                if sym in SYMBOL_TO_ID
            }
        }
        return SourceSnapshot(source=self.name, fetched_at=utc_now(), data=data)
