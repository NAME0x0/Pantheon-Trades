"""Irys (formerly Bundlr) client — permanent Arweave-backed storage.

Irys's HTTP API for uploads accepts pre-signed bundles or a single payload
with a bearer-style JWK key. We use the simple ``POST /tx`` flow with raw
bytes and a content-type tag so retrievals via ``GET /<id>`` return the
expected JSON.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx
import structlog

log = structlog.get_logger("parthenon.irys")

DEFAULT_NODE = "https://node1.irys.xyz"


@dataclass
class IrysConfig:
    node_url: str = DEFAULT_NODE
    jwk_path: str | None = None  # path to wallet JWK json
    token: str = "matic"          # paying currency


class IrysClient:
    def __init__(self, config: IrysConfig | None = None, http: httpx.AsyncClient | None = None) -> None:
        self._config = config or IrysConfig(
            node_url=os.environ.get("IRYS_NODE_URL", DEFAULT_NODE),
            jwk_path=os.environ.get("IRYS_JWK_PATH"),
            token=os.environ.get("IRYS_TOKEN", "matic"),
        )
        self._http = http or httpx.AsyncClient(timeout=30.0)

    def _load_jwk(self) -> dict | None:
        if not self._config.jwk_path:
            return None
        with open(self._config.jwk_path, "rb") as f:
            return json.load(f)

    async def upload_json(self, payload: dict | list, *, tags: dict[str, str] | None = None) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return await self.upload_bytes(raw, content_type="application/json", tags=tags)

    async def upload_bytes(
        self,
        raw: bytes,
        *,
        content_type: str = "application/octet-stream",
        tags: dict[str, str] | None = None,
    ) -> str:
        # The Irys node will reject without a signed bundle in production —
        # the actual signing requires the official irys-js SDK. We wrap the
        # raw upload here so a service-level signer can intercept and sign
        # before forwarding. In dev mode IRYS_JWK_PATH is unset and we no-op.
        if not self._config.jwk_path:
            log.warning("parthenon.irys.no_jwk_skipping_upload", bytes=len(raw))
            return ""
        headers = {"Content-Type": content_type}
        if tags:
            headers["X-Irys-Tags"] = json.dumps(
                [{"name": k, "value": v} for k, v in tags.items()]
            )
        resp = await self._http.post(
            f"{self._config.node_url}/tx/{self._config.token}",
            content=raw,
            headers=headers,
        )
        resp.raise_for_status()
        body = resp.json()
        tx_id = body.get("id") or body.get("tx") or ""
        log.info("parthenon.irys.upload", tx_id=tx_id, bytes=len(raw))
        return tx_id

    async def fetch(self, tx_id: str) -> bytes:
        resp = await self._http.get(f"{self._config.node_url}/{tx_id}")
        resp.raise_for_status()
        return resp.content

    async def close(self) -> None:
        await self._http.aclose()
