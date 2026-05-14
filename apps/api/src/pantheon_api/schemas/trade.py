"""Trade response shape."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TradeSummary(BaseModel):
    trade_id: str
    thesis_id: str
    market_id: str
    direction: Literal["YES", "NO"]
    size_pct: float
    size_usdc: float
    entry_price: float
    fill_price: float | None
    status: str
    order_id: str | None = None
    fill_time: datetime | None = None
    created_at: datetime
