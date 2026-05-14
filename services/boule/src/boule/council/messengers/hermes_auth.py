"""Hermes auth client — fetches signed session tokens from the api gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


@dataclass
class AuthClient:
    http: httpx.AsyncClient
    api_base: str = os.environ.get("PANTHEON_API_URL", "http://api:8000")

    async def me(self, token: str) -> dict:
        r = await self.http.get(
            f"{self.api_base}/auth/me",
            headers={"authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()
