"""Per-category calibration tests."""

from __future__ import annotations

import json
import random

import pytest

from ostrakon.category_calibration import (
    CategoryCalibration,
    apply_calibration,
    apply_platt,
    fit_per_category,
    save_calibrations,
)


def _synthetic_samples(rng: random.Random, agent: str, category: str, n: int,
                       miscalibration_slope: float = 1.0,
                       miscalibration_intercept: float = 0.0):
    """Generate (agent, category, prob, outcome) rows with known
    miscalibration so Platt fit can reverse it."""
    rows = []
    for _ in range(n):
        true_p = rng.uniform(0.05, 0.95)
        # Distort the recorded probability to be systematically off
        raw = max(0.01, min(0.99,
                             1 / (1 + pow(2.71828,
                                          -(miscalibration_slope * (2 * true_p - 1) + miscalibration_intercept)))))
        outcome = 1 if rng.random() < true_p else 0
        rows.append({
            "agent": agent,
            "category": category,
            "probability_estimate": raw,
            "outcome": outcome,
        })
    return rows


def test_fit_per_category_returns_per_agent():
    rng = random.Random(0)
    samples = (
        _synthetic_samples(rng, "ares", "crypto", 60)
        + _synthetic_samples(rng, "ares", "politics", 60)
        + _synthetic_samples(rng, "athena", "crypto", 60)
    )
    cals = fit_per_category(samples)
    assert "ares" in cals
    assert "athena" in cals


def test_fit_per_category_skips_thin_agents():
    rng = random.Random(1)
    samples = _synthetic_samples(rng, "rare_agent", "crypto", 5)
    cals = fit_per_category(samples)
    assert "rare_agent" not in cals


def test_fit_per_category_skips_thin_categories():
    """A category below MIN_PER_CATEGORY inherits the global fit."""
    rng = random.Random(2)
    # 60 crypto + 5 politics for the same agent
    samples = (
        _synthetic_samples(rng, "ares", "crypto", 60)
        + _synthetic_samples(rng, "ares", "politics", 5)
    )
    cals = fit_per_category(samples)
    cal = cals["ares"]
    assert "crypto" in cal.per_category
    assert "politics" not in cal.per_category
    # But the sample-counts entry shows the politics rows existed
    assert cal.sample_counts.get("politics") == 5


def test_apply_calibration_falls_back_to_global():
    """If category-specific cal isn't present, use the global one."""
    rng = random.Random(3)
    samples = _synthetic_samples(rng, "ares", "crypto", 60)
    cals = fit_per_category(samples)
    # 'sports' isn't in this calibration set; should still return a finite prob.
    out = apply_calibration(0.40, agent="ares", category="sports", calibrations=cals)
    assert 0.0 < out < 1.0


def test_apply_calibration_no_agent_passthrough():
    """Unknown agent → return raw probability unchanged."""
    assert apply_calibration(0.42, agent="unknown", category="x", calibrations={}) == 0.42


def test_apply_platt_identity_params():
    """slope=1, intercept=0 ⇒ logistic of x in (0,1)."""
    out = apply_platt(0.5, {"slope": 1.0, "intercept": 0.0})
    # 1/(1+exp(-0.5)) ≈ 0.622
    assert out == pytest.approx(0.6225, abs=0.001)


def test_apply_platt_steeper_slope_pushes_extremes():
    """Slope 10 + small offset moves a 0.6 probability close to 1."""
    out = apply_platt(0.6, {"slope": 10.0, "intercept": 0.0})
    assert out > 0.99


def test_save_calibrations_writes_valid_json(tmp_path):
    cal = CategoryCalibration(
        agent="ares", method="platt",
        global_params={"slope": 1.2, "intercept": -0.1},
        per_category={"crypto": {"slope": 1.5, "intercept": -0.2}},
        sample_counts={"crypto": 60, "politics": 12},
    )
    out_path = tmp_path / "cal.json"
    save_calibrations({"ares": cal}, out_path)
    body = json.loads(out_path.read_text(encoding="utf-8"))
    assert body["agents"]["ares"]["method"] == "platt"
    assert body["agents"]["ares"]["per_category"]["crypto"]["slope"] == 1.5
    assert body["agents"]["ares"]["sample_counts"]["politics"] == 12


def test_fit_unsupported_method_raises():
    rng = random.Random(4)
    samples = _synthetic_samples(rng, "x", "crypto", 60)
    with pytest.raises(NotImplementedError):
        fit_per_category(samples, method="isotonic")  # type: ignore[arg-type]
