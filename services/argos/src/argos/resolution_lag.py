"""Track the lag between a market hitting terminal price and payout settling.

Polymarket markets often quote at a terminal price (>= 0.99 for YES,
<= 0.01 for NO) hours — sometimes days — before the CLOB credits the
payout. Strategos books that as an open position with mark-to-market
PnL, but the cash is unrealised. We want to:

  1. Distinguish OPEN from RESOLVING (market terminal, not yet paid).
  2. Surface STUCK positions whose RESOLVING phase exceeds a threshold.
  3. Persist the transition so Ostrakon can score on observed payout
     not just final-quote PnL.

The tracker is a pure state machine; the caller feeds it ticks of
(position, current_yes_side_price) and (optionally) a payout event,
and it emits the state changes. No Redis / persistence baked in —
the Argos monitor wires it up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

from argos.pnl import Position


class ResolutionState(str, Enum):
    OPEN = "open"
    RESOLVING = "resolving"  # market terminal, awaiting payout
    RESOLVED = "resolved"
    STUCK = "stuck"  # in RESOLVING longer than threshold


# Configurable thresholds.
TERMINAL_THRESHOLD = 0.99  # side-price >= this means the side is winning
STUCK_AFTER = timedelta(hours=6)


@dataclass
class Tracked:
    trade_id: str
    state: ResolutionState = ResolutionState.OPEN
    resolving_since: datetime | None = None
    resolved_at: datetime | None = None


@dataclass
class Transition:
    trade_id: str
    market_id: str
    from_state: ResolutionState
    to_state: ResolutionState
    at: datetime
    note: str = ""


@dataclass
class ResolutionLagTracker:
    terminal_threshold: float = TERMINAL_THRESHOLD
    stuck_after: timedelta = STUCK_AFTER
    _by_trade: dict[str, Tracked] = field(default_factory=dict)

    def state(self, trade_id: str) -> ResolutionState:
        t = self._by_trade.get(trade_id)
        return t.state if t else ResolutionState.OPEN

    def on_tick(self, position: Position, *, now: datetime | None = None) -> Transition | None:
        """Inspect a position and advance its state if needed.

        Returns the Transition that fired, or None if the state is
        unchanged. ``position.current_price`` is the side price we are
        long, so terminal-for-us is when it crosses ``terminal_threshold``.
        """
        now = now or datetime.now(timezone.utc)
        tracked = self._by_trade.setdefault(position.trade_id, Tracked(trade_id=position.trade_id))

        if tracked.state == ResolutionState.RESOLVED:
            return None

        side_terminal = position.current_price >= self.terminal_threshold

        if tracked.state == ResolutionState.OPEN and side_terminal:
            tracked.state = ResolutionState.RESOLVING
            tracked.resolving_since = now
            return Transition(
                trade_id=position.trade_id,
                market_id=position.market_id,
                from_state=ResolutionState.OPEN,
                to_state=ResolutionState.RESOLVING,
                at=now,
                note=f"side at {position.current_price:.4f} >= {self.terminal_threshold}",
            )

        if tracked.state in (ResolutionState.RESOLVING, ResolutionState.STUCK):
            # If the market drifted back below terminal, walk back to OPEN
            # — a quoted "terminal" that retracts is a sign of thin liquidity
            # or a re-listing, not a real resolution.
            if not side_terminal:
                tracked.state = ResolutionState.OPEN
                tracked.resolving_since = None
                return Transition(
                    trade_id=position.trade_id,
                    market_id=position.market_id,
                    from_state=ResolutionState.RESOLVING,
                    to_state=ResolutionState.OPEN,
                    at=now,
                    note="terminal price retracted",
                )
            # Promote to STUCK if we've been waiting too long.
            if (
                tracked.state == ResolutionState.RESOLVING
                and tracked.resolving_since is not None
                and (now - tracked.resolving_since) >= self.stuck_after
            ):
                tracked.state = ResolutionState.STUCK
                return Transition(
                    trade_id=position.trade_id,
                    market_id=position.market_id,
                    from_state=ResolutionState.RESOLVING,
                    to_state=ResolutionState.STUCK,
                    at=now,
                    note=(
                        f"resolving for "
                        f"{(now - tracked.resolving_since).total_seconds() / 3600:.1f}h "
                        f">= {self.stuck_after.total_seconds() / 3600:.1f}h"
                    ),
                )
        return None

    def on_payout(self, trade_id: str, *, now: datetime | None = None) -> Transition | None:
        """Mark a trade RESOLVED. Idempotent — repeat calls are no-ops."""
        now = now or datetime.now(timezone.utc)
        tracked = self._by_trade.get(trade_id)
        if tracked is None:
            tracked = Tracked(trade_id=trade_id, state=ResolutionState.RESOLVING, resolving_since=now)
            self._by_trade[trade_id] = tracked
        if tracked.state == ResolutionState.RESOLVED:
            return None
        prev = tracked.state
        tracked.state = ResolutionState.RESOLVED
        tracked.resolved_at = now
        return Transition(
            trade_id=trade_id,
            market_id="",
            from_state=prev,
            to_state=ResolutionState.RESOLVED,
            at=now,
            note="payout observed",
        )

    def stuck_trades(self) -> list[str]:
        return [tid for tid, t in self._by_trade.items() if t.state == ResolutionState.STUCK]
