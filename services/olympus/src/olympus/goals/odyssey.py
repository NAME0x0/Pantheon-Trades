"""Odyssey goal — long-horizon Sharpe + drawdown across a rolling window."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class OdysseyGoal:
    horizon_days: int = 90
    target_sharpe: float = 1.0
    max_drawdown: float = 0.10
    realised_sharpe: float = 0.0
    realised_drawdown: float = 0.0

    @property
    def status(self) -> str:
        if self.realised_drawdown > self.max_drawdown:
            return "missed"
        if self.realised_sharpe >= self.target_sharpe:
            return "achieved"
        if self.realised_sharpe >= 0.5 * self.target_sharpe:
            return "on_track"
        return "at_risk"


def _sharpe(returns: list[float]) -> float:
    if len(returns) < 3:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / max(len(returns) - 1, 1)
    if var <= 0:
        return 0.0
    return round((mean / math.sqrt(var)) * math.sqrt(250), 4)


def _max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = max(dd, (peak - v) / peak)
    return dd


def evaluate_odyssey(
    returns: list[float],
    equity_curve: list[float],
    *,
    horizon_days: int = 90,
    target_sharpe: float = 1.0,
    max_drawdown: float = 0.10,
) -> OdysseyGoal:
    return OdysseyGoal(
        horizon_days=horizon_days,
        target_sharpe=target_sharpe,
        max_drawdown=max_drawdown,
        realised_sharpe=_sharpe(returns),
        realised_drawdown=round(_max_drawdown(equity_curve), 4),
    )
