"""Thesis response shape for the dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ThesisSummary(BaseModel):
    thesis_id: str
    signal_id: str
    market_id: str
    direction: Literal["YES", "NO"]
    council_probability: float
    raw_market_probability: float
    edge: float
    confidence: float
    recommended_size_pct: float
    weighted_approval: float
    zeus_veto: bool
    solon_veto: bool
    status: str
    archived_cid: str | None = None
    created_at: datetime
