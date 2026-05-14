"""Hashing utilities — content-addressed identifiers for archived artifacts.

The on-chain registry (``ThesisRegistry.sol``) uses ``keccak256`` so any
hash we produce off-chain that has to match on-chain MUST use the same
algorithm. We surface both ``content_hash`` (keccak) and ``sha256_hex``
(for IPFS CIDv0 compatibility) so callers can pick the right one.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

try:  # web3 is a hard dep but keep import isolated for testability
    from eth_utils import keccak as _keccak  # type: ignore[import-untyped]

    def _keccak_hex(data: bytes) -> str:
        return "0x" + _keccak(data).hex()
except ImportError:  # pragma: no cover - fallback for environments without web3
    def _keccak_hex(data: bytes) -> str:
        return "0x" + hashlib.sha3_256(data).hexdigest()


def canonical_json(data: Any) -> bytes:
    """Stable, RFC8785-flavoured canonical JSON encoding used for all hashing."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def content_hash(data: Any) -> str:
    """keccak256 of canonical JSON, hex with ``0x`` prefix."""
    return _keccak_hex(canonical_json(data))


def sha256_hex(data: Any) -> str:
    """sha256 of canonical JSON, hex with ``0x`` prefix."""
    return "0x" + hashlib.sha256(canonical_json(data)).hexdigest()


def thesis_hash(thesis_id: str, market_id: str, council_probability: float, direction: str) -> str:
    """Matches ``ThesisRegistry.sol`` keccak hashing scheme."""
    raw = f"{thesis_id}|{market_id}|{council_probability:.6f}|{direction}".encode("utf-8")
    return _keccak_hex(raw)
