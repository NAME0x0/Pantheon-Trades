"""Tests for the on-chain TVL feature derivation."""

from __future__ import annotations

import pytest

from apollo.features.onchain_tvl import (
    build_feature,
    stablecoin_flow_pct,
    tvl_log_score,
    tvl_rank_score,
)


def test_log_score_zero_or_negative():
    assert tvl_log_score(0) == 0.0
    assert tvl_log_score(-100) == 0.0


def test_log_score_below_floor_clips_to_zero():
    # Floor anchored at $10M.
    assert tvl_log_score(1_000) == 0.0


def test_log_score_above_ceil_clips_to_one():
    # Ceiling anchored at $100B.
    assert tvl_log_score(1e15) == 1.0


def test_log_score_monotonic():
    assert tvl_log_score(1e8) < tvl_log_score(1e9) < tvl_log_score(1e10)


def test_log_score_midpoint_is_half():
    # geometric mean of floor (1e7) and ceil (1e11) is 1e9.
    assert tvl_log_score(1e9) == pytest.approx(0.5, abs=0.05)


def test_rank_score_top_chain_near_one():
    chains = [
        {"name": "smol", "tvl": 1e6},
        {"name": "mid", "tvl": 1e9},
        {"name": "Ethereum", "tvl": 1e11},
    ]
    assert tvl_rank_score("Ethereum", chains) == 1.0


def test_rank_score_unknown_chain():
    chains = [{"name": "Ethereum", "tvl": 1e11}]
    assert tvl_rank_score("nonsense", chains) == 0.0


def test_rank_score_empty():
    assert tvl_rank_score("x", []) == 0.0


def test_build_feature():
    chains = [{"name": "Ethereum", "tvl": 1e10}, {"name": "Solana", "tvl": 1e9}]
    feat = build_feature("Ethereum", chains)
    assert feat.chain == "Ethereum"
    assert feat.tvl_usd == 1e10
    assert 0.0 <= feat.log_score <= 1.0
    assert feat.rank_score == 1.0


def test_build_feature_missing_chain():
    feat = build_feature("Missing", [{"name": "Ethereum", "tvl": 1e10}])
    assert feat.tvl_usd == 0.0
    assert feat.log_score == 0.0


def test_stablecoin_flow_positive():
    assert stablecoin_flow_pct(100, 110) == pytest.approx(0.10)


def test_stablecoin_flow_negative():
    assert stablecoin_flow_pct(100, 80) == pytest.approx(-0.20)


def test_stablecoin_flow_zero_prev_returns_zero():
    assert stablecoin_flow_pct(0, 100) == 0.0
