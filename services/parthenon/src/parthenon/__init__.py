"""Parthenon — archival service for Pantheon Trades.

Pins thesis bundles to IPFS, mirrors permanent copies to Irys, and anchors
their Merkle root on Arc Testnet via the ``ThesisRegistry`` contract. The
``Archive`` class is the single entry point — every other service routes
its archival writes through it.
"""

from parthenon.archive import Archive, ArchiveResult
from parthenon.hash import content_hash, sha256_hex, thesis_hash
from parthenon.ipfs import IpfsClient
from parthenon.manifest import ArchiveManifest, ManifestEntry
from parthenon.merkle import (
    build_merkle_tree,
    leaf_hash,
    merkle_proof,
    onchain_leaf,
    verify_proof,
)

__all__ = [
    "Archive",
    "ArchiveResult",
    "ArchiveManifest",
    "ManifestEntry",
    "IpfsClient",
    "build_merkle_tree",
    "content_hash",
    "leaf_hash",
    "merkle_proof",
    "onchain_leaf",
    "sha256_hex",
    "thesis_hash",
    "verify_proof",
]
