"""DeFiLlama public API — TVL and protocol metrics for DeFi-related markets."""

from __future__ import annotations

import httpx

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

DEFILLAMA = "https://api.llama.fi"


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
