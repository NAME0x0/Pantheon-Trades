"""Paper-trading book — deterministic simulator for evaluation and CI.

Mirrors the live CLOB router's surface (``execute`` / ``cancel`` / ``settle``)
so anything calling Strategos can swap between paper and live by toggling
configuration. Slippage is applied symmetrically; settlement is a single
mark-to-resolution computation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pantheon_core.direction import entry_price as direction_entry_price
from pantheon_core.schema import ApprovalToken, Thesis, Trade, utc_now

from strategos.slippage import estimate_slippage


@dataclass
class PaperBook:
    portfolio_usdc: float = 10_000.0
    trades: list[Trade] = field(default_factory=list)
    realised_pnl_usdc: float = 0.0

    def execute(
        self,
        token: ApprovalToken,
        thesis: Thesis,
        mid_price: float,
        depth_usdc: float = 50_000.0,
    ) -> Trade:
        size_pct = token.final_size_pct or 0.0
        size_usdc = size_pct * self.portfolio_usdc
        side_price = direction_entry_price(mid_price, thesis.direction)
        slippage = estimate_slippage(size_usdc=size_usdc, depth_usdc=depth_usdc)
        # On a YES order, slippage pushes our price up; on NO, down. Symmetric.
        fill = max(0.0, min(1.0, side_price + slippage))
        trade = Trade(
            thesis_id=token.thesis_id,
            market_id=thesis.market_id,
            direction=thesis.direction,
            size_pct=size_pct,
            size_usdc=size_usdc,
            entry_price=side_price,
            status="filled",
            fill_price=fill,
            fill_time=utc_now(),
        )
        self.trades.append(trade)
        return trade

    def settle(self, trade_id: str, resolution_yes_price: float) -> float:
        trade = next((t for t in self.trades if t.trade_id == trade_id), None)
        if trade is None or trade.fill_price is None:
            return 0.0
        resolution_for_side = (
            resolution_yes_price if trade.direction == "YES" else 1.0 - resolution_yes_price
        )
        # Trade was filled at ``fill_price`` for one contract per dollar of
        # ``size_usdc / fill_price`` notional. PnL is (resolution - cost) per contract.
        contracts = trade.size_usdc / trade.fill_price if trade.fill_price > 0 else 0.0
        pnl = (resolution_for_side - trade.fill_price) * contracts
        self.realised_pnl_usdc += pnl
        return pnl
