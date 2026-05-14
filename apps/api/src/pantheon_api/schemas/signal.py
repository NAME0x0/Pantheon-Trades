"""Signal response shape — projects pantheon_core.Signal to dashboard fields."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SignalSummary(BaseModel):
    signal_id: str
    market_id: str
    question: str
    category: str
    band: str
    band_score: float
    edge: float
    edge_abs: float
    market_probability: float
    oracle_probability: float
    liquidity_score: float
    volume_24h: float
    open_interest: float
    spread: float
    staleness_seconds: int
    days_to_resolution: float | None
    created_at: datetime
