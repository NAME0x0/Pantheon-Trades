"""Tests for the resolution-lag tracker."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from argos.pnl import Position
from argos.resolution_lag import ResolutionLagTracker, ResolutionState


def _pos(price: float, trade_id: str = "t1", direction: str = "YES") -> Position:
    return Position(
        trade_id=trade_id,
        market_id="m1",
        direction=direction,  # type: ignore[arg-type]
        entry_price=0.40,
        size_usdc=1000.0,
        entered_at=datetime.now(timezone.utc),
        target=0.55,
        stop=0.30,
        current_price=price,
    )


def test_open_to_resolving_at_terminal():
    tracker = ResolutionLagTracker()
    now = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    p = _pos(price=0.995)
    t = tracker.on_tick(p, now=now)
    assert t is not None
    assert t.from_state == ResolutionState.OPEN
    assert t.to_state == ResolutionState.RESOLVING
    assert tracker.state("t1") == ResolutionState.RESOLVING


def test_open_stays_open_below_terminal():
    tracker = ResolutionLagTracker()
    t = tracker.on_tick(_pos(price=0.60))
    assert t is None
    assert tracker.state("t1") == ResolutionState.OPEN


def test_resolving_to_stuck_after_threshold():
    tracker = ResolutionLagTracker(stuck_after=timedelta(hours=6))
    base = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    tracker.on_tick(_pos(price=0.999), now=base)
    # 7 hours later, still terminal — should fire STUCK.
    t = tracker.on_tick(_pos(price=0.999), now=base + timedelta(hours=7))
    assert t is not None
    assert t.to_state == ResolutionState.STUCK
    assert "t1" in tracker.stuck_trades()


def test_resolving_retract_returns_to_open():
    tracker = ResolutionLagTracker()
    base = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    tracker.on_tick(_pos(price=0.999), now=base)
    # Price retracts below terminal — should walk back to OPEN.
    t = tracker.on_tick(_pos(price=0.80), now=base + timedelta(minutes=10))
    assert t is not None
    assert t.to_state == ResolutionState.OPEN
    assert tracker.state("t1") == ResolutionState.OPEN


def test_on_payout_marks_resolved():
    tracker = ResolutionLagTracker()
    base = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    tracker.on_tick(_pos(price=0.999), now=base)
    t = tracker.on_payout("t1", now=base + timedelta(hours=2))
    assert t is not None
    assert t.to_state == ResolutionState.RESOLVED
    assert tracker.state("t1") == ResolutionState.RESOLVED


def test_on_payout_idempotent():
    tracker = ResolutionLagTracker()
    base = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    tracker.on_payout("t1", now=base)
    again = tracker.on_payout("t1", now=base + timedelta(hours=1))
    assert again is None


def test_resolved_state_blocks_further_ticks():
    tracker = ResolutionLagTracker()
    base = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    tracker.on_payout("t1", now=base)
    # Any further on_tick should be a no-op.
    t = tracker.on_tick(_pos(price=0.999), now=base + timedelta(hours=1))
    assert t is None
    assert tracker.state("t1") == ResolutionState.RESOLVED


def test_no_position_returns_open_state():
    tracker = ResolutionLagTracker()
    assert tracker.state("unknown") == ResolutionState.OPEN


def test_stuck_promotes_only_once_per_pass():
    tracker = ResolutionLagTracker(stuck_after=timedelta(hours=1))
    base = datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)
    tracker.on_tick(_pos(price=0.999), now=base)
    first = tracker.on_tick(_pos(price=0.999), now=base + timedelta(hours=2))
    assert first is not None
    assert first.to_state == ResolutionState.STUCK
    # Subsequent tick at terminal price + already STUCK -> no transition.
    second = tracker.on_tick(_pos(price=0.999), now=base + timedelta(hours=3))
    assert second is None
