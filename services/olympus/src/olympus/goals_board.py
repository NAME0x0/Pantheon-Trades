"""Goals board — high-level objectives Olympus is tracking.

Each goal has a status and a target metric. The board doesn't drive
trades; it surfaces aggregated progress to the dashboard. Goals are
typically things like "weekly Sharpe > 1.0" or "monthly drawdown < 5%".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pantheon_core.schema import utc_now


GoalStatus = Literal["open", "on_track", "at_risk", "achieved", "missed"]


@dataclass
class Goal:
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    metric: str = ""
    target: float = 0.0
    current: float = 0.0
    horizon_days: int = 30
    created_at: datetime = field(default_factory=utc_now)
    status: GoalStatus = "open"

    def update(self, current: float) -> GoalStatus:
        self.current = current
        if self.target > 0:
            ratio = current / self.target
        elif self.target < 0:
            ratio = -current / -self.target if self.target != 0 else 0
        else:
            ratio = 0
        if ratio >= 1.0:
            self.status = "achieved"
        elif ratio >= 0.75:
            self.status = "on_track"
        elif ratio >= 0.4:
            self.status = "at_risk"
        else:
            self.status = "missed"
        return self.status


@dataclass
class GoalsBoard:
    goals: list[Goal] = field(default_factory=list)

    def add(self, goal: Goal) -> None:
        self.goals.append(goal)

    def update(self, goal_id: str, current: float) -> Goal | None:
        for g in self.goals:
            if g.goal_id == goal_id:
                g.update(current)
                return g
        return None

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {"open": 0, "on_track": 0, "at_risk": 0, "achieved": 0, "missed": 0}
        for g in self.goals:
            counts[g.status] = counts.get(g.status, 0) + 1
        return counts
