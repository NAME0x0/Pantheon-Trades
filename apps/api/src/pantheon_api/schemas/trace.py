"""TraceEvent response shape."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TraceEventSummary(BaseModel):
    event_id: str
    trace_id: str
    thesis_id: str
    signal_id: str
    market_id: str
    event_type: str
    agent: str | None = None
    round: int | None = None
    content: str
    tokens: int | None = None
    latency_ms: int | None = None
    vote: Literal["APPROVE", "REJECT", "ABSTAIN"] | None = None
    confidence: float | None = None
    probability_estimate: float | None = None
    flags: list[str] = []
    timestamp: datetime
    sequence: int
