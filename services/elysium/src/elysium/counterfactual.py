"""Counterfactual simulator — re-run history with a single variable perturbed.

Given a backtest's trades + the alternative parameter, ``simulate`` recomputes
realised PnL under the new regime so Olympus can answer "what if we used
quarter-Kelly?", "what if MAX_POSITION_PCT was 3% instead of 5%?", or "what
if Cassandra had veto power?". Returns a delta vs the realised run.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pantheon_core.schema import Trade


@dataclass
class CounterfactualResult:
    label: str
    n_trades: int
    realised_pnl_usdc: float
    counterfactual_pnl_usdc: float

    @property
    def delta_pnl_usdc(self) -> float:
        return round(self.counterfactual_pnl_usdc - self.realised_pnl_usdc, 4)


def resize_trades(trades: list[Trade], new_size_pct: float) -> list[Trade]:
    """Rebuild each trade's size to ``new_size_pct`` of book equity.

    Useful as the input to ``simulate(label="resize", ...)``.
    """
    out: list[Trade] = []
    for t in trades:
        scale = new_size_pct / t.size_pct if t.size_pct else 0.0
        new = t.model_copy(
            update={
                "size_pct": new_size_pct,
                "size_usdc": t.size_usdc * scale,
            }
        )
        out.append(new)
    return out


def simulate(
    label: str,
    realised_trades: list[Trade],
    counterfactual_trades: list[Trade],
    resolve: Callable[[Trade], float],
) -> CounterfactualResult:
    """Score both trade lists with the supplied resolution oracle."""
    def _pnl(trade: Trade) -> float:
        if trade.fill_price is None or trade.fill_price <= 0:
            return 0.0
        payoff = resolve(trade)
        if trade.direction == "NO":
            payoff = 1.0 - payoff
        contracts = trade.size_usdc / trade.fill_price
        return (payoff - trade.fill_price) * contracts

    realised = sum(_pnl(t) for t in realised_trades)
    counter = sum(_pnl(t) for t in counterfactual_trades)
    return CounterfactualResult(
        label=label,
        n_trades=len(counterfactual_trades),
        realised_pnl_usdc=round(realised, 4),
        counterfactual_pnl_usdc=round(counter, 4),
    )
