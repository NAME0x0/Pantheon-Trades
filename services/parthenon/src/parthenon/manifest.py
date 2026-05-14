"""Archive manifest — the parent record that ties one thesis to its artifacts.

A thesis archive is a tree:
    manifest -> thesis CID
             -> trace CID
             -> signal CID
             -> proof_of_restraint CID (if rejected)
             -> [outcome CIDs as they arrive]

The manifest itself is uploaded last so its own CID is the canonical
identifier for the whole archive. The on-chain anchor only stores the
manifest CID, keeping calldata small.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import utc_now


@dataclass
class ManifestEntry:
    kind: str        # "thesis" | "trace" | "signal" | "proof_of_restraint" | "outcome"
    cid: str
    sha256: str
    bytes_count: int


@dataclass
class ArchiveManifest:
    thesis_id: str
    market_id: str
    created_at: datetime = field(default_factory=utc_now)
    entries: list[ManifestEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "thesis_id": self.thesis_id,
            "market_id": self.market_id,
            "created_at": self.created_at.isoformat(),
            "entries": [
                {
                    "kind": e.kind,
                    "cid": e.cid,
                    "sha256": e.sha256,
                    "bytes": e.bytes_count,
                }
                for e in self.entries
            ],
        }

    def add(self, entry: ManifestEntry) -> None:
        self.entries.append(entry)

    def cid_for(self, kind: str) -> str | None:
        for entry in self.entries:
            if entry.kind == kind:
                return entry.cid
        return None
