"""Health probes for Pythia — aggregate freshness of every registered source.

Returns a structured summary safe to expose over HTTP. The API gateway's
``/health`` router fans out to this.
"""

from __future__ import annotations

from dataclasses import dataclass

from pythia.base import DataSource


@dataclass
class HealthEntry:
    source: str
    fresh: bool
    staleness_seconds: int
    max_staleness_seconds: int


def health_for(sources: list[DataSource]) -> list[HealthEntry]:
    out: list[HealthEntry] = []
    for src in sources:
        st = src.staleness_seconds()
        out.append(
            HealthEntry(
                source=src.name,
                fresh=st <= src.max_staleness_seconds,
                staleness_seconds=st,
                max_staleness_seconds=src.max_staleness_seconds,
            )
        )
    return out


def overall_health(entries: list[HealthEntry]) -> str:
    if not entries:
        return "unknown"
    if all(e.fresh for e in entries):
        return "healthy"
    if any(e.fresh for e in entries):
        return "degraded"
    return "down"
