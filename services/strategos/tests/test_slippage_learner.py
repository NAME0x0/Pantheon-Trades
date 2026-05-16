"""Tests for the online slippage learner."""

from __future__ import annotations

from pathlib import Path

import pytest

from strategos.slippage import MAX_SLIPPAGE, estimate_slippage
from strategos.slippage_learner import (
    DEFAULT_DECAY,
    SlippageLearner,
    _depth_bucket,
    _key,
)


def test_no_data_falls_back_to_base():
    learner = SlippageLearner()
    base = estimate_slippage(500, 10_000)
    assert learner.estimate(500, 10_000) == base
    assert learner.estimate(500, 10_000, market_id="m1") == base


def test_positive_bias_increases_estimate():
    learner = SlippageLearner(decay=0.5)
    base = estimate_slippage(500, 10_000)
    # Simulate actual slippage = 2x predicted (book worse than expected).
    learner.observe("m1", actual_slippage=base * 2, size_usdc=500, depth_usdc=10_000)
    est = learner.estimate(500, 10_000, market_id="m1")
    assert est > base


def test_negative_bias_decreases_estimate():
    learner = SlippageLearner(decay=0.5)
    base = estimate_slippage(500, 10_000)
    # Book fills inside the spread — actual better than predicted.
    learner.observe("m1", actual_slippage=0.0, size_usdc=500, depth_usdc=10_000)
    est = learner.estimate(500, 10_000, market_id="m1")
    assert est < base
    assert est >= 0.0


def test_estimate_clamps_to_max():
    learner = SlippageLearner(decay=1.0)
    learner.observe("m1", actual_slippage=1.0, size_usdc=500, depth_usdc=10_000)
    est = learner.estimate(500, 10_000, market_id="m1")
    assert est <= MAX_SLIPPAGE


def test_estimate_clamps_to_zero():
    learner = SlippageLearner(decay=1.0)
    # Big negative observation should still clip to >= 0.
    learner.observe("m1", actual_slippage=-1.0, size_usdc=500, depth_usdc=10_000)
    est = learner.estimate(500, 10_000, market_id="m1")
    assert est >= 0.0


def test_bucket_isolation_per_depth():
    learner = SlippageLearner(decay=1.0)
    learner.observe("m1", actual_slippage=0.05, size_usdc=500, depth_usdc=1_000)
    # Different depth bucket -> different key -> no bias applied.
    est = learner.estimate(500, 100_000, market_id="m1")
    base = estimate_slippage(500, 100_000)
    assert est == base


def test_market_isolation():
    learner = SlippageLearner(decay=1.0)
    learner.observe("m1", actual_slippage=0.05, size_usdc=500, depth_usdc=10_000)
    base = estimate_slippage(500, 10_000)
    assert learner.estimate(500, 10_000, market_id="m2") == base


def test_ewma_converges():
    learner = SlippageLearner(decay=0.5)
    base = estimate_slippage(500, 10_000)
    target_residual = 0.02
    for _ in range(50):
        learner.observe("m1", actual_slippage=base + target_residual, size_usdc=500, depth_usdc=10_000)
    # Bias should now be close to target_residual.
    k = _key("m1", 10_000)
    assert learner.bias[k] == pytest.approx(target_residual, abs=1e-3)


def test_round_trip_json():
    learner = SlippageLearner(decay=0.2)
    learner.observe("m1", actual_slippage=0.04, size_usdc=500, depth_usdc=10_000)
    blob = learner.to_json()
    restored = SlippageLearner.from_json(blob)
    assert restored.decay == 0.2
    assert restored.bias == learner.bias
    assert restored.samples == learner.samples


def test_save_load_round_trip(tmp_path: Path):
    learner = SlippageLearner()
    learner.observe("m1", actual_slippage=0.03, size_usdc=500, depth_usdc=10_000)
    p = tmp_path / "subdir" / "learner.json"
    learner.save(p)
    restored = SlippageLearner.load(p)
    assert restored.bias == learner.bias


def test_load_missing_file_returns_fresh():
    learner = SlippageLearner.load(Path("does_not_exist_anywhere.json"))
    assert learner.bias == {}
    assert learner.decay == DEFAULT_DECAY


def test_observe_ignores_zero_size():
    learner = SlippageLearner()
    learner.observe("m1", actual_slippage=0.05, size_usdc=0.0, depth_usdc=10_000)
    assert learner.bias == {}


def test_depth_bucket_clamps():
    assert _depth_bucket(0.0) == 0
    assert _depth_bucket(0.5) == 0
    assert _depth_bucket(100) == 2
    assert _depth_bucket(1e20) <= 8
