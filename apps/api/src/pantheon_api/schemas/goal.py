"""Goal response shape — exposes a single Olympus goal row."""

from __future__ import annotations

from pydantic import BaseModel


class GoalSummary(BaseModel):
    goal_id: str
    title: str
    description: str = ""
    metric: str
    target: float
    current: float
    horizon_days: int
    status: str
