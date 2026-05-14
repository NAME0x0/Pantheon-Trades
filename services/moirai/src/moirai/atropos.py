"""Atropos — the terminator. Force-ends strategies that breach laws.

Termination triggers from ``MOIRAI_LAWS.md``:
  * Brier degraded above ``TERMINATION_BRIER_THRESHOLD`` for
    ``TERMINATION_BRIER_DAYS`` consecutive days.
  * Drawdown breaches ``TERMINATION_DRAWDOWN_LIMIT``.

Termination is irreversible — once a strategy is TERMINATED, Clotho must
spin a new one (with a new id) rather than reanimate it.
"""

from __future__ import annotations

from dataclasses import dataclass

from moirai.enforcer import MoiraiEnforcer
from moirai.laws import (
    StrategyState,
    TERMINATION_BRIER_THRESHOLD,
    TERMINATION_DRAWDOWN_LIMIT,
)


@dataclass
class TerminationResult:
    terminated: bool
    reason: str


class Atropos:
    def __init__(self, enforcer: MoiraiEnforcer) -> None:
        self._enforcer = enforcer

    def check_and_terminate(self, strategy_id: str) -> TerminationResult:
        rec = self._enforcer.get(strategy_id)
        if rec is None:
            return TerminationResult(False, "strategy not found")
        if rec.state is StrategyState.TERMINATED:
            return TerminationResult(False, "already terminated")
        if rec.drawdown >= TERMINATION_DRAWDOWN_LIMIT:
            return self._kill(strategy_id, f"drawdown {rec.drawdown:.1%} >= {TERMINATION_DRAWDOWN_LIMIT:.0%}")
        if rec.brier_score >= TERMINATION_BRIER_THRESHOLD:
            return self._kill(strategy_id, f"Brier {rec.brier_score:.3f} >= {TERMINATION_BRIER_THRESHOLD}")
        return TerminationResult(False, "no termination trigger")

    def force_terminate(self, strategy_id: str, reason: str) -> TerminationResult:
        return self._kill(strategy_id, reason)

    def _kill(self, strategy_id: str, reason: str) -> TerminationResult:
        ok, msg = self._enforcer.transition(strategy_id, StrategyState.TERMINATED)
        if not ok:
            return TerminationResult(False, msg)
        return TerminationResult(True, reason)
