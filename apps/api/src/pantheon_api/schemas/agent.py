"""Agent roster + scoring shape."""

from __future__ import annotations

from pydantic import BaseModel


class AgentSummary(BaseModel):
    name: str
    role: str
    weight: float
    veto: bool
    credibility_weight: float
    prediction_count: int = 0
