"""Local on-disk storage backend — drop-in replacement for IPFS in dev/CI.

Useful for unit tests and offline development. Artifacts are written to a
content-addressable directory under ``Parthenon's`` local store; the
returned identifier is the sha256 hex so callers can treat it as a CID.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any


class LocalStore:
    def __init__(self, root: str | pathlib.Path) -> None:
        self._root = pathlib.Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def add_json(self, payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return self.add_bytes(raw)

    def add_bytes(self, raw: bytes) -> str:
        h = hashlib.sha256(raw).hexdigest()
        path = self._root / h
        if not path.exists():
            path.write_bytes(raw)
        return h

    def cat(self, identifier: str) -> bytes:
        return (self._root / identifier).read_bytes()

    def exists(self, identifier: str) -> bool:
        return (self._root / identifier).exists()
