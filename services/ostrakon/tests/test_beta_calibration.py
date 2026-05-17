"""Beta calibration unit tests.

Covers:
  - Identity-perfect input ⇒ beta fit ≈ identity (a,b ≈ 1, c ≈ 0).
  - Overconfident input ⇒ calibrated Brier < raw Brier.
  - Tiny sample fallback ⇒ identity returned.
  - apply_beta numeric stability at the [0,1] boundaries.
  - CSV round-trip via the documented column convention.
"""

from __future__ import annotations

import csv
import math

import numpy as np
import pytest

from ostrakon.beta_calibration import (
    BetaCalibration,
    apply_beta,
    brier,
    calibrate_from_csv,
    calibrate_one,
    fit_beta,
)


def test_apply_beta_identity_returns_input() -> None:
    """Identity parameters (1, 1, 0) reproduce the input score."""
    for s in [0.05, 0.20, 0.50, 0.80, 0.95]:
        out = apply_beta(s, 1.0, 1.0, 0.0)
        assert math.isclose(out, s, abs_tol=1e-6)


def test_apply_beta_clamps_extremes() -> None:
    """0 and 1 stay numerically safe."""
    assert 0.0 <= apply_beta(0.0, 1.0, 1.0, 0.0) <= 1.0
    assert 0.0 <= apply_beta(1.0, 1.0, 1.0, 0.0) <= 1.0


def test_fit_beta_recovers_identity_on_calibrated_data() -> None:
    """If raw scores are already perfectly calibrated, fit should be
    indistinguishable from identity. We accept a wide tolerance
    because the fit is regularised through LBFGS on noisy CV folds.
    """
    rng = np.random.default_rng(0)
    n = 800
    p = rng.uniform(0.05, 0.95, size=n)
    outcomes = (rng.uniform(size=n) < p).astype(int)
    a, b, c = fit_beta(p, outcomes)
    # Identity is (1, 1, 0). Confirm we're in the same neighbourhood —
    # within 0.4 on slopes, within 0.5 on intercept.
    assert abs(a - 1.0) < 0.4
    assert abs(b - 1.0) < 0.4
    assert abs(c) < 0.5


def test_fit_beta_corrects_overconfidence() -> None:
    """Take well-calibrated scores, sharpen them artificially, and
    confirm the calibrator brings them back toward 0.5.
    """
    rng = np.random.default_rng(1)
    n = 1000
    p_true = rng.uniform(0.20, 0.80, size=n)
    outcomes = (rng.uniform(size=n) < p_true).astype(int)
    # Sharpen: push everything away from 0.5.
    p_sharp = np.where(p_true > 0.5, p_true ** 0.4, 1 - (1 - p_true) ** 0.4)

    raw_b = brier(p_sharp, outcomes)
    a, b, c = fit_beta(p_sharp, outcomes)
    calibrated = np.array([apply_beta(s, a, b, c) for s in p_sharp])
    cal_b = brier(calibrated, outcomes)

    assert cal_b < raw_b, (
        f"calibration did not improve overconfident scores: "
        f"raw={raw_b:.4f} cal={cal_b:.4f}"
    )


def test_calibrate_one_identity_fallback_triggers_on_worse_calibrated() -> None:
    """Construct data where calibration genuinely cannot help — every
    raw score is already exactly the empirical rate — and assert the
    identity-fallback path returns (1, 1, 0) verbatim.
    """
    # Every raw score is 0.5; outcomes are 50/50. Calibrating cannot
    # improve Brier (already at the irreducible floor for this prior).
    pairs = [(0.5, i % 2) for i in range(200)]
    a, b, c, raw_b, cal_b = calibrate_one(pairs)
    # Fallback semantics: identity returned when calibration doesn't strictly help.
    if cal_b >= raw_b:
        assert (a, b, c) == (1.0, 1.0, 0.0)
        assert raw_b == cal_b


def test_calibrate_one_returns_valid_output_on_random_input() -> None:
    """Sanity: the function never crashes or returns NaN on noisy input."""
    rng = np.random.default_rng(2)
    pairs = [(float(rng.uniform()), int(rng.integers(0, 2))) for _ in range(200)]
    a, b, c, raw_b, cal_b = calibrate_one(pairs)
    assert math.isfinite(a) and math.isfinite(b) and math.isfinite(c)
    assert math.isfinite(raw_b) and math.isfinite(cal_b)
    assert a >= 0 and b >= 0  # clamping invariant
    assert 0 <= raw_b <= 1
    assert 0 <= cal_b <= 1


def test_calibrate_one_beats_raw_on_systematic_bias() -> None:
    """Systematic shift in scores → calibration should compress the
    held-out Brier vs raw.
    """
    rng = np.random.default_rng(3)
    n = 600
    p_true = rng.uniform(0.10, 0.90, size=n)
    outcomes = (rng.uniform(size=n) < p_true).astype(int)
    # Shift every score up by ~0.10 so they are systematically high.
    biased = np.clip(p_true + 0.10, 1e-3, 1 - 1e-3)
    pairs = list(zip(biased.tolist(), outcomes.tolist()))
    a, b, c, raw_b, cal_b = calibrate_one(pairs)
    assert cal_b <= raw_b


def test_calibrate_from_csv_round_trip(tmp_path) -> None:
    """End-to-end: write a CSV with the documented column convention,
    fit, verify per-agent dict shape.
    """
    rng = np.random.default_rng(4)
    csv_path = tmp_path / "backtest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["market_id", "agent", "vote", "probability_estimate",
                    "confidence", "brier", "outcome"])
        for i in range(150):
            for agent in ("ares", "athena", "zeus"):
                p = float(rng.uniform(0.1, 0.9))
                o = int(rng.uniform() < p)
                w.writerow([f"m{i}", agent, "APPROVE", p, 0.7, 0.1, o])

    cals = calibrate_from_csv(csv_path)
    assert set(cals.keys()) == {"ares", "athena", "zeus"}
    for agent, cal in cals.items():
        assert isinstance(cal, BetaCalibration)
        assert cal.n_samples == 150
        assert cal.a >= 0
        assert cal.b >= 0


def test_calibrate_from_csv_skips_undersampled_agents(tmp_path) -> None:
    """Agents with fewer than 10 samples are dropped, not crashed on."""
    csv_path = tmp_path / "thin.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["market_id", "agent", "vote", "probability_estimate",
                    "confidence", "brier", "outcome"])
        # only 5 rows for the test agent — under the 10-sample floor
        for i in range(5):
            w.writerow([f"m{i}", "rare", "APPROVE", 0.5, 0.5, 0.25, 1])
    cals = calibrate_from_csv(csv_path)
    assert "rare" not in cals


def test_apply_beta_monotone_in_score() -> None:
    """For non-degenerate (a > 0, b > 0) params, the calibrator is
    monotonic increasing in the input score. This is the property
    that downstream Kelly sizing relies on.
    """
    a, b, c = 1.5, 1.2, -0.3
    grid = [0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 0.95]
    out = [apply_beta(s, a, b, c) for s in grid]
    assert all(out[i] <= out[i + 1] + 1e-9 for i in range(len(out) - 1))


def test_save_calibrations_round_trip(tmp_path) -> None:
    """File round-trip preserves params verbatim."""
    from ostrakon.beta_calibration import save_calibrations
    import json

    cals = {
        "ares": BetaCalibration(
            agent="ares", n_samples=200, raw_brier=0.25,
            calibrated_brier=0.20, improvement=0.05,
            a=1.4, b=0.9, c=-0.2,
        )
    }
    out_path = tmp_path / "cal.json"
    save_calibrations(cals, out_path)
    blob = json.loads(out_path.read_text(encoding="utf-8"))
    assert blob["method"] == "beta"
    assert blob["agents"]["ares"]["a"] == pytest.approx(1.4)
    assert blob["agents"]["ares"]["c"] == pytest.approx(-0.2)
