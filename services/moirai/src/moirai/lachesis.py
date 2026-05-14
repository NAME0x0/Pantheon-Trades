"""Lachesis — the allocator. Promotes strategies through the lifecycle.

Promotion gates from ``MOIRAI_LAWS.md``:
  * REGISTERED -> PAPER: any time.
  * PAPER -> LIVE: requires PROMOTION_MIN_PAPER_TRADES paper trades, a
    Brier score below PROMOTION_MAX_BRIER, Sharpe above PROMOTION_MIN_SHARPE,
    and win rate above PROMOTION_MIN_WIN_RATE.
  * LIVE -> SUSPENDED: at operator's discretion (no gate; the operator's
    signoff is the gate).
"""

from __future__ import annotations

from dataclasses import dataclass

from moirai.enforcer import MoiraiEnforcer
from moirai.laws import (
    PROMOTION_MAX_BRIER,
    PROMOTION_MIN_PAPER_TRADES,
    PROMOTION_MIN_SHARPE,
    PROMOTION_MIN_WIN_RATE,
    StrategyState,
)


@dataclass
class PromotionResult:
    promoted: bool
    reason: str


class Lachesis:
    def __init__(self, enforcer: MoiraiEnforcer) -> None:
        self._enforcer = enforcer

    def to_paper(self, strategy_id: str) -> tuple[bool, str]:
        return self._enforcer.transition(strategy_id, StrategyState.PAPER)

    def promote(self, strategy_id: str) -> PromotionResult:
        rec = self._enforcer.get(strategy_id)
        if rec is None:
            return PromotionResult(False, "strategy not found")
        if rec.state is not StrategyState.PAPER:
            return PromotionResult(False, f"must be in PAPER (currently {rec.state.value})")
        if rec.paper_trades < PROMOTION_MIN_PAPER_TRADES:
            return PromotionResult(False, f"only {rec.paper_trades} paper trades < {PROMOTION_MIN_PAPER_TRADES}")
        if rec.brier_score > PROMOTION_MAX_BRIER:
            return PromotionResult(False, f"Brier {rec.brier_score:.3f} > {PROMOTION_MAX_BRIER}")
        if rec.sharpe < PROMOTION_MIN_SHARPE:
            return PromotionResult(False, f"Sharpe {rec.sharpe:.2f} < {PROMOTION_MIN_SHARPE}")
        if rec.win_rate < PROMOTION_MIN_WIN_RATE:
            return PromotionResult(False, f"win rate {rec.win_rate:.2%} < {PROMOTION_MIN_WIN_RATE:.0%}")
        ok, msg = self._enforcer.transition(strategy_id, StrategyState.LIVE)
        return PromotionResult(ok, msg)

    def suspend(self, strategy_id: str) -> tuple[bool, str]:
        return self._enforcer.transition(strategy_id, StrategyState.SUSPENDED)
