"""Hermes archive client — forwards to Parthenon's HTTP surface."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class ArchiveClient:
    http: httpx.AsyncClient
    base_url: str = os.environ.get("PARTHENON_URL", "http://parthenon:8007")

    async def replay(self, manifest_cid: str) -> dict:
        r = await self.http.get(f"{self.base_url}/replay/{manifest_cid}")
        r.raise_for_status()
        return r.json()
