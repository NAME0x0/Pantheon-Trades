"""Anomaly detection — flag sudden price moves that warrant attention.

The monitor calls this once per tick per position. Anything anomalous gets
logged and tagged on the next ExitSignal so Strategos and the dashboard can
foreground it.
"""

from __future__ import annotations

from dataclasses import dataclass


JUMP_THRESHOLD = 0.10
STALE_THRESHOLD_SECONDS = 600


@dataclass(frozen=True)
class Anomaly:
    kind: str
    severity: float  # 0..1
    note: str


def detect_jump(prev_price: float, current_price: float) -> Anomaly | None:
    if prev_price <= 0:
        return None
    delta = abs(current_price - prev_price)
    if delta >= JUMP_THRESHOLD:
        severity = min(delta / 0.5, 1.0)
        return Anomaly(
            kind="price_jump",
            severity=severity,
            note=f"{prev_price:.3f} -> {current_price:.3f} ({delta:+.2%})",
        )
    return None


def detect_stale_data(staleness_seconds: int) -> Anomaly | None:
    if staleness_seconds >= STALE_THRESHOLD_SECONDS:
        return Anomaly(
            kind="stale_data",
            severity=min(staleness_seconds / 3600.0, 1.0),
            note=f"staleness {staleness_seconds}s",
        )
    return None
