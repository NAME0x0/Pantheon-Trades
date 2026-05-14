"""Daily Bread goal — track today's realised PnL against a target."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DailyBreadGoal:
    target_usdc: float = 100.0
    realised_usdc: float = 0.0

    def progress(self) -> float:
        if self.target_usdc <= 0:
            return 0.0
        return min(1.0, self.realised_usdc / self.target_usdc)

    @property
    def status(self) -> str:
        p = self.progress()
        if p >= 1.0:
            return "achieved"
        if p >= 0.75:
            return "on_track"
        if p >= 0.40:
            return "at_risk"
        return "missed" if p <= 0.0 else "open"


def evaluate_daily_bread(trades_pnl: list[float], target_usdc: float = 100.0) -> DailyBreadGoal:
    realised = sum(trades_pnl)
    return DailyBreadGoal(target_usdc=target_usdc, realised_usdc=round(realised, 4))
