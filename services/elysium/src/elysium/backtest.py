"""Elysium backtest engine — replay historic signals through Boule+Areopagus.

The engine takes a list of historic ``Signal`` records, a synthetic
deliberation function (typically a fast stub that doesn't burn Claude
tokens), an Areopagus court, and a paper book. It returns a result
bundle: per-trade outcomes, equity curve, Sharpe, Brier across the run.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime

from pantheon_core.schema import ApprovalToken, RejectionRecord, Signal, Thesis, Trade

DeliberateFn = Callable[[Signal], Awaitable[Thesis]]
ResolveFn = Callable[[str, datetime | None], float]


@dataclass
class BacktestResult:
    n_signals: int = 0
    n_theses: int = 0
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    n_rejected: int = 0
    realised_pnl_usdc: float = 0.0
    equity_curve: list[float] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    rejections: list[RejectionRecord] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        total = self.n_wins + self.n_losses
        return self.n_wins / total if total else 0.0

    def summary(self) -> dict[str, float | int]:
        return {
            "n_signals": self.n_signals,
            "n_theses": self.n_theses,
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "n_losses": self.n_losses,
            "n_rejected": self.n_rejected,
            "win_rate": round(self.win_rate, 4),
            "realised_pnl_usdc": round(self.realised_pnl_usdc, 2),
            "final_equity": round(self.equity_curve[-1], 2) if self.equity_curve else 0.0,
            "max_drawdown_pct": round(_max_drawdown_pct(self.equity_curve), 4),
            "sharpe": _equity_sharpe(self.equity_curve),
        }


def _max_drawdown_pct(curve: list[float]) -> float:
    if not curve:
        return 0.0
    peak = curve[0]
    max_dd = 0.0
    for v in curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _equity_sharpe(curve: list[float]) -> float:
    if len(curve) < 3:
        return 0.0
    returns = [
        (curve[i] - curve[i - 1]) / curve[i - 1] if curve[i - 1] > 0 else 0.0
        for i in range(1, len(curve))
    ]
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / max(len(returns) - 1, 1)
    if var <= 0:
        return 0.0
    return round((mean / math.sqrt(var)) * math.sqrt(250), 4)


async def run_backtest(
    signals: Iterable[Signal],
    deliberate: DeliberateFn,
    *,
    court,
    paper,
    resolve: ResolveFn,
) -> BacktestResult:
    """Run signals sequentially through deliberation + gating + paper exec.

    ``court`` is an ``areopagus.court.AreopagusCourt`` and ``paper`` is a
    ``strategos.paper.PaperBook``; the function is intentionally untyped
    for these to keep Elysium decoupled from those packages.
    """
    result = BacktestResult()
    starting_equity = float(getattr(paper, "portfolio_usdc", 10_000.0))
    equity = starting_equity
    result.equity_curve.append(equity)

    for signal in signals:
        result.n_signals += 1
        thesis = await deliberate(signal)
        result.n_theses += 1
        verdict = court.evaluate_thesis(thesis, signal)
        if isinstance(verdict, RejectionRecord):
            result.n_rejected += 1
            result.rejections.append(verdict)
            continue
        assert isinstance(verdict, ApprovalToken)
        trade = paper.execute(
            verdict,
            thesis,
            mid_price=signal.market_probability,
            depth_usdc=signal.volume_24h or 50_000.0,
        )
        result.n_trades += 1
        result.trades.append(trade)
        resolution = resolve(signal.market_id, signal.resolution_date)
        pnl = paper.settle(trade.trade_id, resolution_yes_price=resolution)
        result.realised_pnl_usdc += pnl
        equity += pnl
        result.equity_curve.append(equity)
        if pnl > 0:
            result.n_wins += 1
        elif pnl < 0:
            result.n_losses += 1
    return result
