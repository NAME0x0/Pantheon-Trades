"""Hard lifecycle constants and transition rules for Moirai.

See ``docs/MOIRAI_LAWS.md`` — every constant here ties to a clause that
governs how strategies move through draft, paper, live, and termination.
"""

from __future__ import annotations

from enum import Enum


class StrategyState(str, Enum):
    DRAFT = "DRAFT"
    REGISTERED = "REGISTERED"
    PAPER = "PAPER"
    LIVE = "LIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


VALID_TRANSITIONS: dict[StrategyState, set[StrategyState]] = {
    StrategyState.DRAFT: {StrategyState.REGISTERED, StrategyState.TERMINATED},
    StrategyState.REGISTERED: {StrategyState.PAPER, StrategyState.TERMINATED},
    StrategyState.PAPER: {StrategyState.LIVE, StrategyState.SUSPENDED, StrategyState.TERMINATED},
    StrategyState.LIVE: {StrategyState.SUSPENDED, StrategyState.TERMINATED},
    StrategyState.SUSPENDED: {StrategyState.LIVE, StrategyState.TERMINATED},
    StrategyState.TERMINATED: set(),
}

# Promotion thresholds (PAPER -> LIVE per MOIRAI_LAWS.md)
PROMOTION_MIN_PAPER_TRADES = 10
PROMOTION_MAX_BRIER = 0.25
PROMOTION_MIN_SHARPE = 0.5
PROMOTION_MIN_WIN_RATE = 0.45

# Termination thresholds
TERMINATION_BRIER_THRESHOLD = 0.33
TERMINATION_BRIER_DAYS = 30
TERMINATION_DRAWDOWN_LIMIT = 0.20

# Cooling periods (seconds)
COOLING_FAILED_THESIS = 86400       # 24h
COOLING_DRAWDOWN_10PCT = 172800     # 48h
COOLING_HIGH_REJECTION = 43200      # 12h


def is_valid_transition(current: StrategyState, target: StrategyState) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def transition_error(current: StrategyState, target: StrategyState) -> str:
    allowed = [s.value for s in VALID_TRANSITIONS.get(current, set())]
    return f"Invalid transition {current.value} -> {target.value}. Allowed: {allowed}"
