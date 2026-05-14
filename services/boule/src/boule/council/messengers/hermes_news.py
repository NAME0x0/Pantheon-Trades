"""Hermes news client — pulls aggregated headlines for the council."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class NewsClient:
    http: httpx.AsyncClient
    pythia_base: str = os.environ.get("PYTHIA_URL", "http://pythia:8008")

    async def recent(self, *, limit: int = 25) -> list[dict]:
        r = await self.http.get(f"{self.pythia_base}/news", params={"limit": limit})
        if r.status_code == 404:
            return []
        r.raise_for_status()
        payload = r.json()
        return payload.get("items", [])
