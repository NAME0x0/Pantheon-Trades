"""HermesRouter — single entry point that dispatches to specialised clients.

The council never talks to external systems directly; everything goes
through Hermes. The router holds a shared httpx.AsyncClient and lazily
constructs the right sub-client on demand.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class HermesRouter:
    http: httpx.AsyncClient

    @classmethod
    def from_env(cls) -> "HermesRouter":
        return cls(http=httpx.AsyncClient(timeout=15.0))

    async def close(self) -> None:
        await self.http.aclose()
