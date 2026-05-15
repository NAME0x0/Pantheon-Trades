"""Oracle watch — track Pythia source freshness as a system goal."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OracleWatchGoal:
    fresh_sources: int = 0
    total_sources: int = 0
    worst_staleness_seconds: int = 0
    max_staleness_seconds: int = 300

    @property
    def status(self) -> str:
        if self.total_sources == 0:
            return "unknown"
        ratio = self.fresh_sources / self.total_sources
        if ratio >= 1.0:
            return "achieved"
        if ratio >= 0.5:
            return "at_risk"
        return "missed"


def oracle_health(
    source_staleness: dict[str, int], max_staleness_seconds: int = 300
) -> OracleWatchGoal:
    if not source_staleness:
        return OracleWatchGoal(max_staleness_seconds=max_staleness_seconds)
    fresh = sum(1 for s in source_staleness.values() if s <= max_staleness_seconds)
    return OracleWatchGoal(
        fresh_sources=fresh,
        total_sources=len(source_staleness),
        worst_staleness_seconds=max(source_staleness.values()),
        max_staleness_seconds=max_staleness_seconds,
    )
