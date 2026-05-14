"""Top-level archive orchestrator — what every other service calls.

Other services MUST go through ``Archive`` rather than calling IPFS/Irys
directly (see CLAUDE.md). The orchestrator:

  1. Canonicalises each artifact (signal/thesis/trace).
  2. Pins it to IPFS (or LocalStore in dev mode).
  3. Mirrors it to Irys for permanent storage when configured.
  4. Builds a manifest tying all CIDs together.
  5. Computes a Merkle root over the artifact hashes.
  6. Returns ``ArchiveResult`` with the manifest CID and Merkle root so the
     caller (Boule / Strategos) can hand it off to ``anchor.AnchorService``
     for the on-chain witness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from pantheon_core.schema import Signal, Thesis, TraceEvent

from parthenon.hash import canonical_json, content_hash, sha256_hex
from parthenon.ipfs import IpfsClient
from parthenon.irys import IrysClient
from parthenon.manifest import ArchiveManifest, ManifestEntry
from parthenon.merkle import build_merkle_tree

log = structlog.get_logger("parthenon.archive")


@dataclass
class ArchiveResult:
    manifest_cid: str
    merkle_root: str
    manifest: ArchiveManifest


class Archive:
    def __init__(
        self,
        ipfs: IpfsClient,
        irys: IrysClient | None = None,
    ) -> None:
        self._ipfs = ipfs
        self._irys = irys

    async def _put(self, kind: str, payload: Any, manifest: ArchiveManifest) -> ManifestEntry:
        raw = canonical_json(payload)
        cid = await self._ipfs.add_bytes(raw, pin=True)
        if self._irys is not None:
            try:
                await self._irys.upload_bytes(raw, content_type="application/json", tags={"kind": kind})
            except Exception as e:
                log.warning("parthenon.irys_mirror_failed", kind=kind, error=str(e))
        entry = ManifestEntry(
            kind=kind,
            cid=cid,
            sha256=sha256_hex(payload),
            bytes_count=len(raw),
        )
        manifest.add(entry)
        return entry

    async def archive_thesis_bundle(
        self,
        signal: Signal,
        thesis: Thesis,
        trace: list[TraceEvent],
    ) -> ArchiveResult:
        manifest = ArchiveManifest(thesis_id=thesis.thesis_id, market_id=thesis.market_id)
        await self._put("signal", signal.model_dump(mode="json"), manifest)
        await self._put("thesis", thesis.model_dump(mode="json"), manifest)
        await self._put("trace", [t.model_dump(mode="json") for t in trace], manifest)

        # Merkle root is over the keccak content hashes of each entry.
        leaves = [content_hash(payload) for payload in (
            signal.model_dump(mode="json"),
            thesis.model_dump(mode="json"),
            [t.model_dump(mode="json") for t in trace],
        )]
        root, _layers = build_merkle_tree(leaves)

        manifest_cid = await self._ipfs.add_json(manifest.to_dict(), pin=True)
        log.info(
            "parthenon.archived_thesis",
            thesis_id=thesis.thesis_id,
            manifest_cid=manifest_cid,
            merkle_root=root,
        )
        return ArchiveResult(manifest_cid=manifest_cid, merkle_root=root, manifest=manifest)

    async def archive_outcome(
        self,
        manifest: ArchiveManifest,
        outcome: dict,
    ) -> str:
        entry = await self._put("outcome", outcome, manifest)
        manifest_cid = await self._ipfs.add_json(manifest.to_dict(), pin=True)
        log.info("parthenon.archived_outcome", manifest_cid=manifest_cid, cid=entry.cid)
        return manifest_cid
