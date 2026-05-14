"""Exit rules — decide whether and why to close an open position.

Every rule produces an ``ExitSignal`` if it fires, else None. The Argos
monitor evaluates them in priority order: invalidation (thesis-killer)
takes precedence over stops, which take precedence over targets, which
take precedence over time-based expiry.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from pantheon_core.schema import ExitSignal, utc_now

from argos.pnl import Position


INVALIDATION_DRIFT = 0.10  # 10pp adverse move from entry = invalidation
DEFAULT_MAX_HOLD_DAYS = 90


def _signal(position: Position, reason: str) -> ExitSignal:
    return ExitSignal(
        trade_id=position.trade_id,
        market_id=position.market_id,
        reason=reason,  # type: ignore[arg-type]
        current_price=position.current_price,
    )


def check_target(position: Position) -> ExitSignal | None:
    return _signal(position, "target_hit") if position.target_hit else None


def check_stop(position: Position) -> ExitSignal | None:
    return _signal(position, "stop_loss") if position.stop_hit else None


def check_invalidation(position: Position) -> ExitSignal | None:
    """Triggered when our side has drifted ``INVALIDATION_DRIFT`` against us."""
    if position.entry_price <= 0:
        return None
    adverse = position.entry_price - position.current_price
    if adverse >= INVALIDATION_DRIFT:
        return _signal(position, "invalidation")
    return None


def check_expiry(position: Position, max_hold_days: int = DEFAULT_MAX_HOLD_DAYS) -> ExitSignal | None:
    age = utc_now() - position.entered_at
    if age >= timedelta(days=max_hold_days):
        return _signal(position, "expiry")
    return None


def check_exit(position: Position, max_hold_days: int = DEFAULT_MAX_HOLD_DAYS) -> ExitSignal | None:
    """Apply all exit rules in priority order."""
    for rule in (check_invalidation, check_stop, check_target):
        sig = rule(position)
        if sig is not None:
            return sig
    return check_expiry(position, max_hold_days=max_hold_days)
