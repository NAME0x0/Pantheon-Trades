"""Exile registry — agents banned from council deliberation.

An agent is exiled when its credibility weight crosses below
``EXILE_MIN_CREDIBILITY`` for ``EXILE_PERSISTENCE_DAYS`` consecutive days.
Exile is reversible: a returning agent must pass ``REINSTATEMENT_DAYS`` of
clean prediction performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from pantheon_core.schema import utc_now


EXILE_MIN_CREDIBILITY = 0.55
EXILE_PERSISTENCE_DAYS = 7
REINSTATEMENT_DAYS = 14


@dataclass
class ExileRecord:
    agent: str
    exiled_at: datetime
    reason: str
    review_at: datetime


@dataclass
class ExileRegistry:
    records: dict[str, ExileRecord] = field(default_factory=dict)

    def exile(self, agent: str, reason: str, now: datetime | None = None) -> ExileRecord:
        ts = now or utc_now()
        record = ExileRecord(
            agent=agent,
            exiled_at=ts,
            reason=reason,
            review_at=ts + timedelta(days=REINSTATEMENT_DAYS),
        )
        self.records[agent] = record
        return record

    def is_exiled(self, agent: str, now: datetime | None = None) -> bool:
        rec = self.records.get(agent)
        if rec is None:
            return False
        return (now or utc_now()) < rec.review_at

    def reinstate(self, agent: str) -> bool:
        return self.records.pop(agent, None) is not None
