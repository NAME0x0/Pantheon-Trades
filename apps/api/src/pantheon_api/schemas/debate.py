"""Debate transcript envelope shape."""

from __future__ import annotations

from pydantic import BaseModel

from pantheon_api.schemas.trace import TraceEventSummary


class DebateEnvelope(BaseModel):
    trace_id: str
    events: list[TraceEventSummary]
    count: int
