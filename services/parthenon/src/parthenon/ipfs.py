"""IPFS HTTP API client — pins JSON artifacts via Kubo or a remote pinning service.

We intentionally restrict ourselves to the ``add`` and ``cat`` endpoints
plus a pinning helper. Any node speaking the Kubo HTTP API (Infura, Pinata,
self-hosted Kubo) works.

Output is the CIDv1 string returned by the daemon. We assume the calling
service supplies the canonical JSON bytes — Parthenon's job is to push
them, not to canonicalise them again.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger("parthenon.ipfs")


@dataclass
class IpfsConfig:
    api_url: str
    auth_header: str | None = None  # e.g. "Bearer <token>" for Infura/Pinata


class IpfsClient:
    """Thin async client over Kubo HTTP API or compatible pinning services."""

    def __init__(self, config: IpfsConfig, http: httpx.AsyncClient | None = None) -> None:
        self._config = config
        self._http = http or httpx.AsyncClient(timeout=30.0)

    @classmethod
    def from_env(cls) -> "IpfsClient":
        return cls(
            IpfsConfig(
                api_url=os.environ.get("IPFS_API_URL", "http://localhost:5001"),
                auth_header=os.environ.get("IPFS_AUTH"),
            )
        )

    def _headers(self) -> dict[str, str]:
        if self._config.auth_header:
            return {"Authorization": self._config.auth_header}
        return {}

    async def add_json(self, payload: dict | list, *, pin: bool = True) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return await self.add_bytes(raw, pin=pin)

    async def add_bytes(self, raw: bytes, *, pin: bool = True) -> str:
        params = {"pin": "true" if pin else "false", "cid-version": "1"}
        files = {"file": ("artifact.json", raw, "application/json")}
        resp = await self._http.post(
            f"{self._config.api_url}/api/v0/add",
            params=params,
            files=files,
            headers=self._headers(),
        )
        resp.raise_for_status()
        # Kubo returns NDJSON; pick the last record.
        last_line = resp.text.strip().splitlines()[-1]
        parsed = json.loads(last_line)
        cid = parsed.get("Hash") or parsed.get("cid")
        if not cid:
            raise RuntimeError(f"unexpected IPFS response: {parsed}")
        log.info("parthenon.ipfs.add", cid=cid, bytes=len(raw))
        return cid

    async def cat(self, cid: str) -> bytes:
        resp = await self._http.post(
            f"{self._config.api_url}/api/v0/cat",
            params={"arg": cid},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.content

    async def close(self) -> None:
        await self._http.aclose()
