"""Position PnL accounting for prediction-market positions.

Every position is stored in *side-price* space: ``entry_price`` and
``current_price`` are both the price of the side we are long, regardless of
whether that is YES or NO. That makes PnL a single formula:

    pnl_pct = (current_price - entry_price) / entry_price

and target/stop comparisons are always "current >= target" / "current <=
stop" without YES/NO branching. The caller (Argos monitor) is responsible
for converting Polymarket's YES-side spot price to side price using the
direction stored on the trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


Direction = Literal["YES", "NO"]


@dataclass
class Position:
    trade_id: str
    market_id: str
    direction: Direction
    entry_price: float  # side price we paid (in [0, 1])
    size_usdc: float
    entered_at: datetime
    target: float  # side price at which we take profit
    stop: float    # side price at which we cut losses
    current_price: float = 0.0

    @property
    def contracts(self) -> float:
        return self.size_usdc / self.entry_price if self.entry_price > 0 else 0.0

    @property
    def pnl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price

    @property
    def pnl_usdc(self) -> float:
        return self.pnl_pct * self.size_usdc

    @property
    def target_hit(self) -> bool:
        return self.current_price >= self.target

    @property
    def stop_hit(self) -> bool:
        return self.current_price <= self.stop

    def update(self, yes_side_price: float) -> None:
        """Update current_price from the YES-side spot price."""
        self.current_price = yes_side_price if self.direction == "YES" else 1.0 - yes_side_price


def compute_portfolio_pnl(positions: list[Position]) -> float:
    return sum(p.pnl_usdc for p in positions)


def total_exposure_usdc(positions: list[Position]) -> float:
    return sum(p.size_usdc for p in positions)
