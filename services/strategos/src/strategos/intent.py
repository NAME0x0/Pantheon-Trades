"""Trade intent — the abstract order specification before signing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pantheon_core.direction import entry_price as direction_entry_price
from pantheon_core.schema import ApprovalToken, Thesis


@dataclass(frozen=True)
class TradeIntent:
    thesis_id: str
    market_id: str
    direction: Literal["YES", "NO"]
    side_price: float
    size_usdc: float
    contracts: float
    yes_token_id: str | None
    no_token_id: str | None

    @property
    def selected_token_id(self) -> str | None:
        return self.yes_token_id if self.direction == "YES" else self.no_token_id


def build_intent(
    token: ApprovalToken,
    thesis: Thesis,
    *,
    mid_price: float,
    portfolio_usdc: float,
    yes_token_id: str | None,
    no_token_id: str | None,
) -> TradeIntent:
    size_pct = token.final_size_pct or 0.0
    size_usdc = size_pct * portfolio_usdc
    side = direction_entry_price(mid_price, thesis.direction)
    contracts = size_usdc / side if side > 0 else 0.0
    return TradeIntent(
        thesis_id=thesis.thesis_id,
        market_id=thesis.market_id,
        direction=thesis.direction,
        side_price=round(side, 6),
        size_usdc=round(size_usdc, 6),
        contracts=round(contracts, 6),
        yes_token_id=yes_token_id,
        no_token_id=no_token_id,
    )
