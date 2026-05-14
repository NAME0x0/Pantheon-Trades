from __future__ import annotations

from parthenon.hash import content_hash, sha256_hex, thesis_hash
from parthenon.merkle import build_merkle_tree, merkle_proof, verify_proof


def test_content_hash_deterministic():
    h1 = content_hash({"a": 1, "b": 2})
    h2 = content_hash({"b": 2, "a": 1})
    assert h1 == h2
    assert h1.startswith("0x")


def test_sha256_hex_deterministic():
    assert sha256_hex({"a": 1}) == sha256_hex({"a": 1})


def test_thesis_hash():
    h = thesis_hash("tid", "0xmarket", 0.72, "YES")
    assert h.startswith("0x")
    assert len(h) == 66


def test_merkle_single_leaf():
    leaf = sha256_hex({"x": 1})
    root, layers = build_merkle_tree([leaf])
    assert root.startswith("0x")
    assert len(layers) == 1


def test_merkle_proof_verify():
    leaves = [sha256_hex({"i": i}) for i in range(4)]
    root, layers = build_merkle_tree(leaves)
    for idx, leaf in enumerate(leaves):
        proof = merkle_proof(layers, idx)
        assert verify_proof(leaf, proof, root), f"index {idx} should verify"


def test_merkle_proof_rejects_wrong_leaf():
    leaves = [sha256_hex({"i": i}) for i in range(4)]
    root, layers = build_merkle_tree(leaves)
    proof = merkle_proof(layers, 0)
    bogus_leaf = sha256_hex({"i": 99})
    assert not verify_proof(bogus_leaf, proof, root)


def test_merkle_odd_count():
    leaves = [sha256_hex({"i": i}) for i in range(5)]
    root, layers = build_merkle_tree(leaves)
    for idx, leaf in enumerate(leaves):
        proof = merkle_proof(layers, idx)
        assert verify_proof(leaf, proof, root), f"index {idx} should verify"
