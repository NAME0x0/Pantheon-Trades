"""Merkle tree primitives — used by the on-chain registry to verify archives.

The tree uses the same hash function as the rest of Parthenon's on-chain
hashing (keccak256) so a proof produced here verifies directly against
``ThesisRegistry.verifyProof``. Pair-hashing uses concatenation in the same
order Solidity's ``abi.encodePacked`` would emit, with the standard
OpenZeppelin convention of *sorted* pair ordering — this lets us omit the
left/right sibling direction from proofs.
"""

from __future__ import annotations

import hashlib

try:
    from eth_utils import keccak as _keccak  # type: ignore[import-untyped]

    def _hash(data: bytes) -> bytes:
        return _keccak(data)
except ImportError:  # pragma: no cover
    def _hash(data: bytes) -> bytes:
        return hashlib.sha3_256(data).digest()


def _to_bytes(item: str | bytes) -> bytes:
    if isinstance(item, bytes):
        return item
    s = item[2:] if item.startswith("0x") else item
    return bytes.fromhex(s)


def _hash_pair(a: bytes, b: bytes) -> bytes:
    return _hash(a + b) if a <= b else _hash(b + a)


def leaf_hash(leaf: str | bytes) -> str:
    return "0x" + _hash(_to_bytes(leaf) if not isinstance(leaf, bytes) else leaf).hex()


def build_merkle_tree(leaves: list[str]) -> tuple[str, list[list[str]]]:
    """Build a Merkle tree.

    Each ``leaves`` entry should already be a hex-encoded hash (with or
    without the ``0x`` prefix). The first layer hashes each leaf again so
    raw content cannot be passed through as a node.
    """
    if not leaves:
        empty = "0x" + _hash(b"").hex()
        return empty, [[]]

    layer = [_hash(_to_bytes(l)) for l in leaves]
    layers: list[list[bytes]] = [layer]

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer = layer + [layer[-1]]
        layer = [_hash_pair(layer[i], layer[i + 1]) for i in range(0, len(layer), 2)]
        layers.append(layer)

    hex_layers = [[("0x" + n.hex()) for n in lyr] for lyr in layers]
    root = hex_layers[-1][0]
    return root, hex_layers


def merkle_proof(layers: list[list[str]], leaf_index: int) -> list[str]:
    """Generate an OpenZeppelin-style proof (siblings only, sorted-pair hashing)."""
    proof: list[str] = []
    idx = leaf_index
    for layer in layers[:-1]:
        sibling_idx = idx + 1 if idx % 2 == 0 else idx - 1
        if 0 <= sibling_idx < len(layer):
            proof.append(layer[sibling_idx])
        else:
            proof.append(layer[idx])  # duplicated odd leaf
        idx //= 2
    return proof


def verify_proof(leaf: str, proof: list[str], root: str) -> bool:
    current = _hash(_to_bytes(leaf))
    for sibling_hex in proof:
        sibling = _to_bytes(sibling_hex)
        current = _hash_pair(current, sibling)
    return ("0x" + current.hex()) == root
