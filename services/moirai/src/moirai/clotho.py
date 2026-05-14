"""Clotho — the spinner. Creates new strategies in DRAFT state.

A strategy is a parametric thesis-generator. Clotho's only job is to
materialise a new ``StrategyRecord`` with a stable id and a unique name.
Promotion to PAPER is Lachesis's job; termination is Atropos's.
"""

from __future__ import annotations

import uuid

from moirai.enforcer import MoiraiEnforcer, StrategyRecord
from moirai.laws import StrategyState


class Clotho:
    def __init__(self, enforcer: MoiraiEnforcer) -> None:
        self._enforcer = enforcer

    def spin(self, name: str) -> StrategyRecord:
        rec = StrategyRecord(
            strategy_id=str(uuid.uuid4()),
            name=name,
            state=StrategyState.DRAFT,
        )
        self._enforcer.register(rec)
        return rec

    def register(self, strategy_id: str) -> tuple[bool, str]:
        return self._enforcer.transition(strategy_id, StrategyState.REGISTERED)
