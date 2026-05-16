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
