"""Feature cache — TTL-bounded scored Signal per market_id.

Keeps the last-scored Signal so a market that has not changed materially
between two scan ticks reuses the prior result. Fresh tick fully
overwrites; reads honour a soft TTL beyond which the cache miss falls
through to the full scorer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from pantheon_core.schema import Signal


DEFAULT_TTL_SECONDS = 60.0


@dataclass
class _Entry:
    signal: Signal
    stored_at: float


@dataclass
class FeatureCache:
    ttl_seconds: float = DEFAULT_TTL_SECONDS
    _entries: dict[str, _Entry] = field(default_factory=dict)

    def get(self, market_id: str) -> Signal | None:
        entry = self._entries.get(market_id)
        if entry is None:
            return None
        if time.monotonic() - entry.stored_at > self.ttl_seconds:
            self._entries.pop(market_id, None)
            return None
        return entry.signal

    def put(self, market_id: str, signal: Signal) -> None:
        self._entries[market_id] = _Entry(signal=signal, stored_at=time.monotonic())

    def invalidate(self, market_id: str) -> None:
        self._entries.pop(market_id, None)

    def size(self) -> int:
        return len(self._entries)
