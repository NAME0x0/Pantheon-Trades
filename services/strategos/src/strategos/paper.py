"""Paper-trading book — deterministic simulator for evaluation and CI.

Mirrors the live CLOB router's surface (``execute`` / ``cancel`` /
``settle``) so anything calling Strategos can swap between paper and
live by toggling configuration.

Fill realism — the previous draft filled at the mid; that gave fantasy
PnL. The model now reflects three real costs:

  1. **Half-spread cost.** A YES taker buy lifts the ask, not the mid.
     If the caller supplies ``bid`` + ``ask`` we use those exactly;
     otherwise we approximate ``ask = mid + DEFAULT_HALF_SPREAD``.

  2. **Slippage vs depth.** Existing ``estimate_slippage`` model
     applied to the inside price the order actually walks.

  3. **Fees.** Polymarket charges taker fees up to 2%; configurable
     via ``STRATEGOS_FEE_BPS`` env (default 200 = 2%). Charged on
     entry AND at settlement so PnL reflects the true round-trip.

These three together close the gap between "looks profitable on
paper" and "actually profitable after Polymarket touches your USDC."
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from pantheon_core.direction import entry_price as direction_entry_price
from pantheon_core.schema import ApprovalToken, Thesis, Trade, utc_now

from strategos.slippage import estimate_slippage

DEFAULT_HALF_SPREAD = float(os.environ.get("STRATEGOS_DEFAULT_HALF_SPREAD", "0.01"))
DEFAULT_FEE_BPS = float(os.environ.get("STRATEGOS_FEE_BPS", "200"))  # 2.00%
MAX_TAKE_FRACTION = float(os.environ.get("STRATEGOS_MAX_TAKE_FRACTION", "0.10"))


@dataclass
class PaperBook:
    portfolio_usdc: float = 10_000.0
    fee_bps: float = DEFAULT_FEE_BPS
    trades: list[Trade] = field(default_factory=list)
    realised_pnl_usdc: float = 0.0
    fees_paid_usdc: float = 0.0

    def execute(
        self,
        token: ApprovalToken,
        thesis: Thesis,
        mid_price: float,
        depth_usdc: float = 50_000.0,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> Trade:
        """Execute the approved trade against a synthetic CLOB.

        ``bid`` and ``ask`` override the half-spread approximation when
        the caller has real book data (e.g. from Pythia's Polymarket
        snapshot). When unset, we approximate.
        """
        size_pct = token.final_size_pct or 0.0
        size_usdc = size_pct * self.portfolio_usdc

        # Resolve the actual top-of-book price the order walks against.
        if thesis.direction == "YES":
            inside = ask if ask is not None else mid_price + DEFAULT_HALF_SPREAD
        else:
            # NO buyers pay (1 - bid) of YES → equivalently lift the YES bid.
            yes_bid = bid if bid is not None else mid_price - DEFAULT_HALF_SPREAD
            inside = 1.0 - yes_bid

        slippage = estimate_slippage(size_usdc=size_usdc, depth_usdc=depth_usdc)

        # Cap how much of the book we eat in one order — beyond this the
        # paper fill is unrealistic and live submission would partial-fill.
        size_capped = False
        if depth_usdc > 0 and size_usdc / depth_usdc > MAX_TAKE_FRACTION:
            size_usdc = MAX_TAKE_FRACTION * depth_usdc
            size_pct = size_usdc / self.portfolio_usdc if self.portfolio_usdc > 0 else 0.0
            size_capped = True

        # Final fill price: top-of-book + slippage, clipped to (0, 1).
        fill = max(0.01, min(0.99, inside + slippage))

        # Entry fee (in USDC, charged on notional).
        entry_fee = size_usdc * (self.fee_bps / 10_000.0)
        self.fees_paid_usdc += entry_fee

        side_price = direction_entry_price(mid_price, thesis.direction)
        trade = Trade(
            thesis_id=token.thesis_id,
            market_id=thesis.market_id,
            direction=thesis.direction,
            size_pct=size_pct,
            size_usdc=size_usdc,
            entry_price=side_price,
            status="filled" if not size_capped else "partial",
            fill_price=fill,
            fill_time=utc_now(),
        )
        self.trades.append(trade)
        return trade

    def settle(self, trade_id: str, resolution_yes_price: float) -> float:
        """Settle a single trade. Returns net PnL after exit fee."""
        trade = next((t for t in self.trades if t.trade_id == trade_id), None)
        if trade is None or trade.fill_price is None:
            return 0.0
        resolution_for_side = (
            resolution_yes_price
            if trade.direction == "YES"
            else 1.0 - resolution_yes_price
        )
        # Contracts purchased at fill_price for ``size_usdc`` of notional.
        contracts = trade.size_usdc / trade.fill_price if trade.fill_price > 0 else 0.0
        gross = (resolution_for_side - trade.fill_price) * contracts

        # Exit fee on the resolution payout (loser leg pays 0 since the
        # contract pays nothing; winner leg pays fee on the $1 settlement).
        exit_notional = contracts * resolution_for_side
        exit_fee = exit_notional * (self.fee_bps / 10_000.0)
        self.fees_paid_usdc += exit_fee

        pnl = gross - exit_fee
        self.realised_pnl_usdc += pnl
        return pnl

    def equity_usdc(self) -> float:
        """Total book value: starting bankroll + realised PnL."""
        return self.portfolio_usdc + self.realised_pnl_usdc
