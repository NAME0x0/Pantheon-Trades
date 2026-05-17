"""Tests for the maker/taker execution-mode chooser."""

from __future__ import annotations

from strategos.execution_mode import (
    MAKER_EPSILON,
    MAKER_MAX_EDGE,
    choose_execution,
)


def test_taker_when_urgent():
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.07,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=2.0,  # < min_days_for_maker
    )
    assert d.mode == "taker"
    assert "urgent" in d.reason


def test_taker_when_high_conviction():
    d = choose_execution(
        side_price=0.45,
        edge_abs=MAKER_MAX_EDGE + 0.01,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=30.0,
    )
    assert d.mode == "taker"
    assert "high conviction" in d.reason


def test_taker_when_size_dominates_depth():
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.06,
        depth_usdc=1000,
        size_usdc=500,  # 50% of depth
        days_to_resolution=30.0,
    )
    assert d.mode == "taker"
    assert "size/depth" in d.reason


def test_taker_when_depth_zero():
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.06,
        depth_usdc=0.0,
        size_usdc=500,
        days_to_resolution=30.0,
    )
    assert d.mode == "taker"


def test_maker_when_all_conditions_met():
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.07,
        depth_usdc=200_000,
        size_usdc=500,
        days_to_resolution=30.0,
    )
    assert d.mode == "maker"
    # Maker posts inside the spread by epsilon.
    assert d.limit_price == 0.45 - MAKER_EPSILON


def test_taker_price_is_above_side():
    d = choose_execution(
        side_price=0.40,
        edge_abs=0.30,  # forces taker
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=30.0,
    )
    assert d.mode == "taker"
    assert d.limit_price >= 0.40  # crossed spread + slip


def test_no_days_means_patient():
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.07,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=None,
    )
    assert d.mode == "maker"


def test_maker_falls_back_at_unit_edge():
    d = choose_execution(
        side_price=0.015,  # epsilon below pushes below 0.01 floor
        edge_abs=0.07,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=30.0,
    )
    assert d.mode == "taker"


def test_limit_price_clipped_to_unit():
    # Side price near top, big slip — taker should clip at 0.99.
    d = choose_execution(
        side_price=0.98,
        edge_abs=0.4,
        depth_usdc=10.0,  # forces big slip
        size_usdc=10_000,
        days_to_resolution=1.0,
    )
    assert 0.01 <= d.limit_price <= 0.99


# ─── post_only + maker-rebate plumbing (Polymarket V2) ────────────────


def test_maker_decision_sets_post_only_true():
    """Maker decisions must carry post_only=True so Polymarket V2
    rejects (rather than crosses) if the spread gets snipped."""
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.06,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=30.0,
        category="politics",
    )
    assert d.mode == "maker"
    assert d.post_only is True


def test_taker_decision_does_not_set_post_only():
    """Taker decisions must explicitly clear post_only — a taker order
    with post_only would be rejected by the exchange."""
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.40,  # high conviction → taker
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=30.0,
        category="politics",
    )
    assert d.mode == "taker"
    assert d.post_only is False


def test_category_fee_bps_routed_to_decision():
    """Crypto category fee (720 bps peak) is surfaced on the decision
    so downstream accounting can subtract it from PnL."""
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.4,  # taker
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=1.0,
        category="crypto",
    )
    assert d.expected_taker_fee_bps == 720
    assert d.expected_maker_rebate_bps == 0.0


def test_geopolitics_category_is_fee_free():
    """Geopolitics is fee-free in Polymarket V2 (March 2026 schedule)."""
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.4,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=1.0,
        category="geopolitics",
    )
    assert d.expected_taker_fee_bps == 0.0


def test_maker_rebate_proportional_to_taker_fee():
    """Maker rebate bps = MAKER_REBATE_SHARE * taker fee bps for the
    same category. For politics (400 bps) at 22% share = 88 bps."""
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.06,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=30.0,
        category="politics",
    )
    assert d.mode == "maker"
    # 400 bps * 0.22 = 88 bps
    assert abs(d.expected_maker_rebate_bps - 88.0) < 0.5


def test_unknown_category_falls_back_to_other():
    """Unknown categories use the 'other' fee tier (500 bps)."""
    d = choose_execution(
        side_price=0.45,
        edge_abs=0.4,
        depth_usdc=100_000,
        size_usdc=500,
        days_to_resolution=1.0,
        category="unknown_made_up",
    )
    assert d.expected_taker_fee_bps == 500
