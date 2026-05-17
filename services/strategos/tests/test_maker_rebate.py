"""Tests for the maker_rebate ledger.

We test the accounting math, not exchange behaviour. Every fee + rebate
matches the V2 schedule for the category. Edge cases: unknown
categories, zero-notional trades, mixed maker/taker flow.
"""

from __future__ import annotations

import pytest

from strategos.maker_rebate import (
    MAKER_REBATE_SHARE,
    TAKER_FEE_BPS_BY_CATEGORY,
    FeeLedger,
    project_savings,
)


def test_taker_books_full_fee_no_rebate():
    """Politics 400 bps × $1000 notional = $40 fee, $0 rebate."""
    ledger = FeeLedger()
    row = ledger.book(
        trade_id="t1",
        market_id="m1",
        category="politics",
        mode="taker",
        notional_usdc=1000.0,
    )
    assert row.fee_paid_usdc == pytest.approx(40.0)
    assert row.rebate_accrued_usdc == 0.0
    assert row.effective_bps == 400.0


def test_maker_books_rebate_no_fee():
    """Politics 400 bps × $1000 × 22% rebate share = $8.80 rebate."""
    ledger = FeeLedger()
    row = ledger.book(
        trade_id="t2",
        market_id="m1",
        category="politics",
        mode="maker",
        notional_usdc=1000.0,
    )
    assert row.fee_paid_usdc == 0.0
    assert row.rebate_accrued_usdc == pytest.approx(8.80)
    # Effective bps is negative — we earned, didn't pay.
    assert row.effective_bps == pytest.approx(-88.0)


def test_geopolitics_zero_fee_and_zero_rebate():
    """V2 sets geopolitics fee = 0. Both legs net to zero."""
    ledger = FeeLedger()
    t = ledger.book(trade_id="t1", market_id="m", category="geopolitics",
                    mode="taker", notional_usdc=1000.0)
    m = ledger.book(trade_id="t2", market_id="m", category="geopolitics",
                    mode="maker", notional_usdc=1000.0)
    assert t.fee_paid_usdc == 0.0
    assert m.rebate_accrued_usdc == 0.0


def test_unknown_category_falls_back_to_other():
    """Made-up category routes to 'other' (500 bps)."""
    ledger = FeeLedger()
    row = ledger.book(trade_id="t1", market_id="m", category="lemurs_riding_bikes",
                      mode="taker", notional_usdc=1000.0)
    assert row.nominal_fee_bps == 500.0
    assert row.fee_paid_usdc == pytest.approx(50.0)


def test_none_category_falls_back_to_other():
    ledger = FeeLedger()
    row = ledger.book(trade_id="t1", market_id="m", category=None,
                      mode="taker", notional_usdc=1000.0)
    assert row.nominal_fee_bps == 500.0


def test_zero_notional_is_zero_fee():
    ledger = FeeLedger()
    row = ledger.book(trade_id="t1", market_id="m", category="crypto",
                      mode="taker", notional_usdc=0.0)
    assert row.fee_paid_usdc == 0.0
    assert row.rebate_accrued_usdc == 0.0


def test_negative_notional_clamped_to_zero():
    """Defensive: a negative notional should never produce negative fees."""
    ledger = FeeLedger()
    row = ledger.book(trade_id="t1", market_id="m", category="crypto",
                      mode="taker", notional_usdc=-100.0)
    assert row.fee_paid_usdc == 0.0
    assert row.notional_usdc == 0.0


def test_unknown_mode_raises():
    ledger = FeeLedger()
    with pytest.raises(ValueError):
        ledger.book(trade_id="t1", market_id="m", category="crypto",
                    mode="weirdmode", notional_usdc=100.0)  # type: ignore[arg-type]


def test_totals_aggregates_across_trades():
    ledger = FeeLedger()
    # 2 taker crypto trades + 1 maker politics trade
    ledger.book(trade_id="t1", market_id="m", category="crypto",
                mode="taker", notional_usdc=1000.0)
    ledger.book(trade_id="t2", market_id="m", category="crypto",
                mode="taker", notional_usdc=2000.0)
    ledger.book(trade_id="t3", market_id="n", category="politics",
                mode="maker", notional_usdc=1000.0)
    tot = ledger.totals()
    # 720 bps × $3000 taker = $216 fees. + 0 from maker.
    assert tot["fees_paid_usdc"] == pytest.approx(216.0)
    # 400 bps × $1000 × 22% maker = $8.80 rebates.
    assert tot["rebates_accrued_usdc"] == pytest.approx(8.80)
    assert tot["net_cost_usdc"] == pytest.approx(216.0 - 8.80)
    assert tot["trades"] == 3.0


def test_by_category_segments_correctly():
    ledger = FeeLedger()
    ledger.book(trade_id="t1", market_id="m", category="crypto",
                mode="taker", notional_usdc=1000.0)
    ledger.book(trade_id="t2", market_id="m", category="politics",
                mode="taker", notional_usdc=500.0)
    by_cat = ledger.by_category()
    assert set(by_cat.keys()) == {"crypto", "politics"}
    assert by_cat["crypto"]["trades"] == 1
    assert by_cat["politics"]["trades"] == 1
    assert by_cat["crypto"]["fees_paid_usdc"] == pytest.approx(72.0)
    assert by_cat["politics"]["fees_paid_usdc"] == pytest.approx(20.0)


def test_project_savings_returns_positive_savings_under_mixed_flow():
    """Going 50% maker on politics flow should save real money."""
    s = project_savings(
        n_trades_per_day=10,
        avg_notional_usdc=1000.0,
        maker_share=0.5,
        category="politics",
    )
    assert s["annual_savings_usdc"] > 0
    # All-taker round-trip is 2 × 400 = 800 bps. Mixed (50% maker entry,
    # always taker exit) = 0.5 × 800 + 0.5 × (400 - 88) = 400 + 156 = 556 bps.
    # Saving = 800 - 556 = 244 bps per round trip.
    assert s["bps_saved_per_round_trip"] == pytest.approx(244.0, abs=1.0)


def test_table_constants_match_documented_v2_schedule():
    """Smoke check on the V2 fee schedule. If Polymarket changes it,
    this test fails noisily — operator updates the table + retests."""
    assert TAKER_FEE_BPS_BY_CATEGORY["crypto"] == 720
    assert TAKER_FEE_BPS_BY_CATEGORY["sports"] == 300
    assert TAKER_FEE_BPS_BY_CATEGORY["politics"] == 400
    assert TAKER_FEE_BPS_BY_CATEGORY["geopolitics"] == 0
    assert TAKER_FEE_BPS_BY_CATEGORY["world_events"] == 0
    assert TAKER_FEE_BPS_BY_CATEGORY["other"] == 500
    assert MAKER_REBATE_SHARE == 0.22
