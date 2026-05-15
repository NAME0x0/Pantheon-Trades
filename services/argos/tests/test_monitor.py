from __future__ import annotations

from datetime import datetime, timezone

from argos.anomaly import detect_jump, detect_stale_data
from argos.exits import check_exit, check_invalidation, check_stop, check_target
from argos.pnl import Position


def _pos(direction="YES", **overrides) -> Position:
    base = dict(
        trade_id="t1",
        market_id="m1",
        direction=direction,
        entry_price=0.40,
        size_usdc=1000.0,
        entered_at=datetime.now(timezone.utc),
        target=0.55,
        stop=0.30,
        current_price=0.40,
    )
    base.update(overrides)
    return Position(**base)


def test_yes_position_pnl():
    p = _pos()
    p.update(yes_side_price=0.50)
    assert abs(p.pnl_pct - 0.25) < 1e-9
    assert abs(p.pnl_usdc - 250.0) < 1e-9


def test_no_position_pnl():
    p = _pos(direction="NO", entry_price=0.60, target=0.75, stop=0.50)
    p.update(yes_side_price=0.30)  # NO side = 0.70
    assert abs(p.current_price - 0.70) < 1e-9
    assert p.pnl_pct > 0


def test_check_target_hits():
    p = _pos(current_price=0.56)
    sig = check_target(p)
    assert sig is not None and sig.reason == "target_hit"


def test_check_stop_hits():
    p = _pos(current_price=0.29)
    sig = check_stop(p)
    assert sig is not None and sig.reason == "stop_loss"


def test_check_invalidation():
    p = _pos(entry_price=0.50, current_price=0.38)
    sig = check_invalidation(p)
    assert sig is not None and sig.reason == "invalidation"


def test_check_exit_priority():
    p = _pos(entry_price=0.60, current_price=0.45, target=0.70, stop=0.55)
    # adverse > INVALIDATION_DRIFT (0.10): invalidation should fire before stop.
    sig = check_exit(p)
    assert sig is not None
    assert sig.reason in ("invalidation", "stop_loss")


def test_anomaly_jump_detection():
    a = detect_jump(0.40, 0.55)
    assert a is not None and a.kind == "price_jump"
    assert detect_jump(0.40, 0.41) is None


def test_anomaly_stale_data():
    a = detect_stale_data(700)
    assert a is not None and a.kind == "stale_data"
    assert detect_stale_data(60) is None
