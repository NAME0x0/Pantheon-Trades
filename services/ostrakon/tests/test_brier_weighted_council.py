"""Brier-weighted council aggregation tests."""

from __future__ import annotations

import pytest

from ostrakon.brier_weighted_council import (
    AgentVote,
    CouncilWeights,
    aggregate,
    compute_briers,
    compute_weights,
    diversity,
    fit_weights,
)


def test_compute_briers_basic():
    history = [
        {"agent": "ares", "probability_estimate": 0.8, "outcome": 1},  # err=0.04
        {"agent": "ares", "probability_estimate": 0.7, "outcome": 1},  # err=0.09
        {"agent": "athena", "probability_estimate": 0.5, "outcome": 0},  # err=0.25
    ]
    briers, counts = compute_briers(history)
    assert briers["ares"] == pytest.approx(0.065)
    assert briers["athena"] == pytest.approx(0.25)
    assert counts == {"ares": 2, "athena": 1}


def test_compute_briers_skips_malformed():
    history = [
        {"agent": "ares", "probability_estimate": "bad", "outcome": 1},
        {"agent": "ares", "probability_estimate": 0.5, "outcome": 1},
    ]
    briers, counts = compute_briers(history)
    assert counts["ares"] == 1


def test_compute_weights_favors_lower_brier():
    """Agent with lower Brier should get higher weight."""
    briers = {"good": 0.05, "bad": 0.25}
    w = compute_weights(briers, tau=0.05, floor=0.0)
    assert w["good"] > w["bad"]


def test_compute_weights_temperature_controls_sharpness():
    """Low tau → near winner-take-all. High tau → near-uniform."""
    briers = {"good": 0.05, "bad": 0.25}
    w_sharp = compute_weights(briers, tau=0.01, floor=0.0)
    w_soft = compute_weights(briers, tau=1.0, floor=0.0)
    # Sharper temperature → bigger weight gap.
    assert w_sharp["good"] / w_sharp["bad"] > w_soft["good"] / w_soft["bad"]


def test_compute_weights_sum_to_one():
    briers = {"a": 0.10, "b": 0.20, "c": 0.30}
    w = compute_weights(briers, tau=0.05)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)


def test_compute_weights_floor_prevents_zero():
    """No agent gets zero weight even with extreme Brier."""
    briers = {"a": 0.01, "b": 0.49}
    w = compute_weights(briers, tau=0.01, floor=0.05)
    # b's weight should be at least the floor share (5%)
    assert w["b"] > 0.02


def test_compute_weights_empty_input():
    assert compute_weights({}) == {}


def test_fit_weights_end_to_end():
    history = [
        {"agent": "good", "probability_estimate": 0.9, "outcome": 1},
        {"agent": "good", "probability_estimate": 0.1, "outcome": 0},
        {"agent": "bad", "probability_estimate": 0.5, "outcome": 1},
        {"agent": "bad", "probability_estimate": 0.5, "outcome": 0},
    ]
    cw = fit_weights(history)
    assert cw.weights["good"] > cw.weights["bad"]
    assert cw.sample_counts == {"good": 2, "bad": 2}


def test_aggregate_uniform_when_no_weights():
    votes = [AgentVote("a", 0.4), AgentVote("b", 0.6)]
    p = aggregate(votes, weights=None)
    assert p == pytest.approx(0.5)


def test_aggregate_respects_weights():
    """High-weight agent dominates the aggregate."""
    votes = [AgentVote("good", 0.8), AgentVote("bad", 0.2)]
    cw = CouncilWeights(weights={"good": 0.9, "bad": 0.1}, briers={}, sample_counts={})
    p = aggregate(votes, weights=cw)
    # 0.9*0.8 + 0.1*0.2 = 0.74
    assert p == pytest.approx(0.74)


def test_aggregate_empty_votes():
    assert aggregate([]) == 0.5


def test_aggregate_clamps_extreme_probabilities():
    """Probabilities outside [0.01, 0.99] are clamped before averaging."""
    votes = [AgentVote("a", 1.5), AgentVote("b", -0.2)]  # absurd
    p = aggregate(votes)
    # Clamped to 0.99 and 0.01 → mean 0.50
    assert p == pytest.approx(0.50)


def test_diversity_zero_with_unanimous():
    votes = [AgentVote("a", 0.5), AgentVote("b", 0.5), AgentVote("c", 0.5)]
    assert diversity(votes) == 0.0


def test_diversity_positive_with_disagreement():
    votes = [AgentVote("a", 0.1), AgentVote("b", 0.5), AgentVote("c", 0.9)]
    assert diversity(votes) > 0.3


def test_diversity_single_vote_zero():
    assert diversity([AgentVote("a", 0.6)]) == 0.0
