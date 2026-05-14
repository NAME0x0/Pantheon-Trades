"""Archive validation — confirm fetched bytes match their content hash."""

from __future__ import annotations

import json

from parthenon.hash import content_hash, sha256_hex


def validate_against_sha256(raw: bytes, expected_sha256: str) -> bool:
    payload = json.loads(raw)
    return sha256_hex(payload).lower() == expected_sha256.lower()


def validate_against_keccak(raw: bytes, expected_keccak: str) -> bool:
    payload = json.loads(raw)
    return content_hash(payload).lower() == expected_keccak.lower()
