"""War-room alerts — surface critical incidents to the dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pantheon_core.schema import utc_now


Severity = Literal["info", "warning", "critical"]


@dataclass
class WarRoomAlert:
    kind: str
    severity: Severity
    note: str
    at: datetime = field(default_factory=utc_now)


@dataclass
class WarRoomGoal:
    open_alerts: list[WarRoomAlert] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.open_alerts if a.severity == "critical")

    @property
    def status(self) -> str:
        if self.critical_count > 0:
            return "at_risk"
        if self.open_alerts:
            return "open"
        return "achieved"


def war_room_alerts(
    *,
    drawdown_pct: float,
    consecutive_losses: int,
    services_unhealthy: int,
) -> WarRoomGoal:
    goal = WarRoomGoal()
    if drawdown_pct >= 0.10:
        goal.open_alerts.append(
            WarRoomAlert(
                kind="drawdown",
                severity="critical" if drawdown_pct >= 0.15 else "warning",
                note=f"daily drawdown {drawdown_pct:.1%}",
            )
        )
    if consecutive_losses >= 5:
        goal.open_alerts.append(
            WarRoomAlert(
                kind="loss_streak",
                severity="warning",
                note=f"{consecutive_losses} consecutive losses",
            )
        )
    if services_unhealthy >= 1:
        goal.open_alerts.append(
            WarRoomAlert(
                kind="service_health",
                severity="critical" if services_unhealthy >= 2 else "warning",
                note=f"{services_unhealthy} critical services unhealthy",
            )
        )
    return goal
