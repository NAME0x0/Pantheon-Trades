"""Staleness aggregation utilities — quantify how old fused snapshots are.

A single market snapshot is built by composing data from several sources
(Polymarket book, CoinGecko price, news, Reddit). We surface the worst-case
staleness so Areopagus can hard-gate any signal whose data backbone has
drifted past policy.
"""

from __future__ import annotations

from datetime import datetime

from pantheon_core.schema import utc_now


def staleness_for(timestamps: list[datetime]) -> int:
    """Return age in seconds of the oldest contributing timestamp."""
    if not timestamps:
        return 999_999
    now = utc_now()
    return max(int((now - ts).total_seconds()) for ts in timestamps if ts is not None)


def is_fresh(timestamps: list[datetime], max_age_seconds: int = 300) -> bool:
    return staleness_for(timestamps) <= max_age_seconds
