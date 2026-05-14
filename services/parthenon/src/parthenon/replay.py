"""Replay tools — reconstruct a thesis from its archive manifest.

Useful for the dashboard's trace viewer and for Underworld post-mortems.
"""

from __future__ import annotations

import json
from typing import Any

from parthenon.ipfs import IpfsClient
from parthenon.manifest import ArchiveManifest


async def load_manifest(ipfs: IpfsClient, manifest_cid: str) -> ArchiveManifest:
    raw = await ipfs.cat(manifest_cid)
    payload = json.loads(raw)
    manifest = ArchiveManifest(
        thesis_id=payload["thesis_id"],
        market_id=payload["market_id"],
    )
    from datetime import datetime

    manifest.created_at = datetime.fromisoformat(payload["created_at"])
    from parthenon.manifest import ManifestEntry

    manifest.entries = [
        ManifestEntry(
            kind=e["kind"],
            cid=e["cid"],
            sha256=e["sha256"],
            bytes_count=int(e.get("bytes", 0)),
        )
        for e in payload.get("entries", [])
    ]
    return manifest


async def replay_thesis(ipfs: IpfsClient, manifest_cid: str) -> dict[str, Any]:
    manifest = await load_manifest(ipfs, manifest_cid)
    bundle: dict[str, Any] = {"manifest_cid": manifest_cid, "manifest": manifest.to_dict()}
    for entry in manifest.entries:
        try:
            raw = await ipfs.cat(entry.cid)
            bundle[entry.kind] = json.loads(raw)
        except Exception:
            bundle[entry.kind] = None
    return bundle
