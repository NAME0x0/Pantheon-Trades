"""Boule memory store — recent thesis outcomes per market.

Keep a ring buffer of the last N thesis results per market_id so agents
can be reminded that they previously voted on this market and how it
resolved. Surfaced inside agent prompts via ``memory.recall``.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime

from pantheon_core.schema import utc_now


@dataclass(frozen=True)
class MemoryEntry:
    market_id: str
    thesis_id: str
    direction: str
    council_probability: float
    outcome: str  # "win" | "loss" | "push" | "pending"
    at: datetime


class MemoryStore:
    def __init__(self, capacity: int = 32) -> None:
        self._by_market: dict[str, deque[MemoryEntry]] = defaultdict(
            lambda: deque(maxlen=capacity)
        )

    def record(
        self,
        market_id: str,
        thesis_id: str,
        direction: str,
        council_probability: float,
        outcome: str = "pending",
    ) -> None:
        self._by_market[market_id].append(
            MemoryEntry(
                market_id=market_id,
                thesis_id=thesis_id,
                direction=direction,
                council_probability=council_probability,
                outcome=outcome,
                at=utc_now(),
            )
        )

    def recent(self, market_id: str, n: int = 5) -> list[MemoryEntry]:
        return list(self._by_market.get(market_id, ()))[-n:]

    def has_history(self, market_id: str) -> bool:
        return bool(self._by_market.get(market_id))
