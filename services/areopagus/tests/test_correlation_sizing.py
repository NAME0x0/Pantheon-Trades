"""Tests for correlation-aware portfolio sizing."""

from __future__ import annotations

import pytest

from areopagus.correlation_sizing import correlation_aware_size


def test_empty_book_unchanged():
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="m1",
        open_market_ids=[],
        pairwise_corr={},
    )
    assert out.adjusted_size == 0.05
    assert out.multiplier == 1.0
    assert out.max_corr == 0.0
    assert out.note == "empty_book"


def test_no_correlation_unchanged():
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["mlb-yankees"],
        pairwise_corr={("btc-120k", "mlb-yankees"): 0.0},
    )
    assert out.adjusted_size == pytest.approx(0.05, rel=1e-9)
    assert out.multiplier == 1.0


def test_high_correlation_downsizes():
    """0.8 correlation → multiplier 0.2 → size 0.05 × 0.2 = 0.01."""
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["btc-150k"],
        pairwise_corr={("btc-120k", "btc-150k"): 0.8},
    )
    assert out.max_corr == 0.8
    assert out.multiplier == pytest.approx(0.2, abs=1e-9)
    assert out.adjusted_size == pytest.approx(0.01, abs=1e-9)


def test_min_multiplier_floor_applies():
    """Perfectly correlated → multiplier clamped at min_multiplier, not 0."""
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["btc-clone"],
        pairwise_corr={("btc-120k", "btc-clone"): 1.0},
        min_multiplier=0.2,
    )
    assert out.multiplier == 0.2
    assert out.adjusted_size == pytest.approx(0.01, abs=1e-9)


def test_max_over_book():
    """Picks the largest |corr| across open positions."""
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["sol-200", "btc-150k", "mlb"],
        pairwise_corr={
            ("btc-120k", "sol-200"): 0.4,
            ("btc-120k", "btc-150k"): 0.7,
            ("btc-120k", "mlb"): 0.05,
        },
    )
    assert out.max_corr == pytest.approx(0.7, abs=1e-9)
    assert "btc-150k" in out.note


def test_negative_correlation_uses_absolute():
    """A perfectly inversely-correlated open position should also reduce size."""
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["short-btc-120k"],
        pairwise_corr={("btc-120k", "short-btc-120k"): -0.9},
    )
    assert out.max_corr == 0.9
    assert out.multiplier < 1.0


def test_bidirectional_lookup():
    """Matrix stored (a, b) is found when looking up (b, a) too."""
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["btc-150k"],
        pairwise_corr={("btc-150k", "btc-120k"): 0.6},  # stored other way round
    )
    assert out.max_corr == 0.6


def test_missing_pair_treated_as_zero_corr():
    """Markets not in the matrix contribute zero (we cannot assume)."""
    out = correlation_aware_size(
        raw_size_pct=0.05,
        market_id="btc-120k",
        open_market_ids=["unknown"],
        pairwise_corr={},
    )
    assert out.max_corr == 0.0
    assert out.adjusted_size == 0.05
    assert out.note == "no_corr_data"
