"""ProofOfRestraint response shape."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RestraintSummary(BaseModel):
    proof_id: str
    signal_id: str
    market_id: str
    reason_code: str
    note: str
    signal_hash: str
    tx_hash: str | None = None
    created_at: datetime
