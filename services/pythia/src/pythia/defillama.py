"""DeFiLlama public API — TVL and protocol metrics for DeFi-related markets."""

from __future__ import annotations

import httpx

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

DEFILLAMA = "https://api.llama.fi"
STABLECOINS_BASE = "https://stablecoins.llama.fi"
YIELDS_BASE = "https://yields.llama.fi"


class DefiLlamaSource(DataSource):
    name = "defillama"
    max_staleness_seconds = 300

    def __init__(self, client: httpx.AsyncClient, protocols: list[str] | None = None) -> None:
        super().__init__(client)
        self._protocols = protocols or []

    async def fetch(self) -> SourceSnapshot:
        if not self._protocols:
            resp = await self._client.get(f"{DEFILLAMA}/protocols", timeout=15.0)
            resp.raise_for_status()
            return SourceSnapshot(
                source=self.name,
                fetched_at=utc_now(),
                data={"protocols": resp.json()},
            )
        results: dict[str, dict] = {}
        for slug in self._protocols:
            try:
                r = await self._client.get(f"{DEFILLAMA}/protocol/{slug}", timeout=15.0)
                r.raise_for_status()
                results[slug] = r.json()
            except httpx.HTTPError:
                continue
        return SourceSnapshot(source=self.name, fetched_at=utc_now(), data={"protocols": results})

    async def total_tvl(self) -> float:
        resp = await self._client.get(f"{DEFILLAMA}/tvl", timeout=10.0)
        resp.raise_for_status()
        return float(resp.json())

    # ── extended endpoints ──

    async def chains(self) -> list[dict]:
        """Per-chain current TVL snapshot."""
        resp = await self._client.get(f"{DEFILLAMA}/v2/chains", timeout=15.0)
        resp.raise_for_status()
        out = resp.json()
        return out if isinstance(out, list) else []

    async def chain_tvl(self, chain: str) -> float:
        """Current TVL for a specific chain, in USD. 0 if unknown."""
        for row in await self.chains():
            if str(row.get("name", "")).lower() == chain.lower():
                try:
                    return float(row.get("tvl", 0.0))
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    async def stablecoin_snapshot(self) -> dict:
        """Top-level stablecoin marketcap snapshot."""
        resp = await self._client.get(
            f"{STABLECOINS_BASE}/stablecoins",
            params={"includePrices": "true"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def stablecoin_total_marketcap(self) -> float:
        """Sum of peggedUSD across all stablecoins."""
        snap = await self.stablecoin_snapshot()
        peggeds = snap.get("peggedAssets") or snap.get("stablecoins") or []
        total = 0.0
        for entry in peggeds:
            try:
                cap = entry.get("circulating", {}).get("peggedUSD", 0.0)
                total += float(cap)
            except (TypeError, ValueError, AttributeError):
                continue
        return total

    async def pool_yields(self) -> list[dict]:
        """All yield pools tracked by DeFiLlama yields module."""
        resp = await self._client.get(f"{YIELDS_BASE}/pools", timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        # The API returns {"status": "success", "data": [...]}.
        if isinstance(data, dict):
            return data.get("data", []) or []
        return data if isinstance(data, list) else []
