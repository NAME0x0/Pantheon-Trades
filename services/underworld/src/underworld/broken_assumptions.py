"""Broken-assumption registry — claims that reality disproved."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import utc_now


@dataclass(frozen=True)
class BrokenAssumption:
    thesis_id: str
    market_id: str
    assumption: str
    note: str = ""
    at: datetime = field(default_factory=utc_now)


@dataclass
class BrokenAssumptionRegistry:
    entries: list[BrokenAssumption] = field(default_factory=list)

    def record(
        self, thesis_id: str, market_id: str, assumption: str, note: str = ""
    ) -> BrokenAssumption:
        record = BrokenAssumption(
            thesis_id=thesis_id, market_id=market_id, assumption=assumption, note=note
        )
        self.entries.append(record)
        return record

    def by_kind(self) -> Counter:
        return Counter(e.assumption for e in self.entries)

    def for_market(self, market_id: str) -> list[BrokenAssumption]:
        return [e for e in self.entries if e.market_id == market_id]
