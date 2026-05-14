from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from pantheon_core.schema import utc_now

from moirai.laws import (
    COOLING_DRAWDOWN_10PCT,
    COOLING_FAILED_THESIS,
    COOLING_HIGH_REJECTION,
    StrategyState,
    is_valid_transition,
    transition_error,
)


@dataclass
class StrategyRecord:
    strategy_id: str
    name: str
    state: StrategyState = StrategyState.DRAFT
    paper_trades: int = 0
    brier_score: float = 0.0
    sharpe: float = 0.0
    win_rate: float = 0.0
    drawdown: float = 0.0
    cooling_until: datetime | None = None
    last_transition: datetime = field(default_factory=utc_now)
    history: list[tuple[str, str, datetime]] = field(default_factory=list)


class MoiraiEnforcer:
    """Enforces strategy lifecycle laws."""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategyRecord] = {}

    def register(self, strategy: StrategyRecord) -> None:
        self._strategies[strategy.strategy_id] = strategy

    def get(self, strategy_id: str) -> StrategyRecord | None:
        return self._strategies.get(strategy_id)

    def all(self) -> list[StrategyRecord]:
        return list(self._strategies.values())

    def transition(self, strategy_id: str, target: StrategyState) -> tuple[bool, str]:
        rec = self._strategies.get(strategy_id)
        if rec is None:
            return False, f"Unknown strategy {strategy_id}"
        if not is_valid_transition(rec.state, target):
            return False, transition_error(rec.state, target)
        old = rec.state
        rec.state = target
        rec.last_transition = utc_now()
        rec.history.append((old.value, target.value, rec.last_transition))
        return True, f"{old.value} -> {target.value}"

    def is_eligible_for_deliberation(self, strategy_id: str) -> tuple[bool, str]:
        rec = self._strategies.get(strategy_id)
        if rec is None:
            return False, "strategy not found"
        if rec.state not in (StrategyState.PAPER, StrategyState.LIVE):
            return False, f"strategy in {rec.state.value} state, not eligible"
        now = utc_now()
        if rec.cooling_until and now < rec.cooling_until:
            remaining = int((rec.cooling_until - now).total_seconds())
            return False, f"cooling period active ({remaining}s remaining)"
        return True, "eligible"

    def apply_cooling(self, strategy_id: str, reason: str) -> None:
        rec = self._strategies.get(strategy_id)
        if rec is None:
            return
        periods = {
            "failed_thesis": COOLING_FAILED_THESIS,
            "drawdown_10pct": COOLING_DRAWDOWN_10PCT,
            "high_rejection": COOLING_HIGH_REJECTION,
        }
        seconds = periods.get(reason, COOLING_FAILED_THESIS)
        rec.cooling_until = utc_now() + timedelta(seconds=seconds)
