"""Conformal-prediction unit tests.

Covers:
  * Coverage property — on a calibrated sample, intervals contain the
    realised outcome at least (1 - α) of the time.
  * Quantile finite-sample correction — q_hat behaves at the alpha
    boundary.
  * Adaptive (time-decayed) quantile differs from the static one when
    recent and older error distributions diverge.
  * conservative_kelly_p returns the right bound per direction.
"""

from __future__ import annotations

import random

import pytest

from ostrakon.conformal_calibration import (
    adaptive_quantile,
    conservative_kelly_p,
    fit_intervals,
    interval,
    split_quantile,
)


def test_split_quantile_empty_returns_max_width():
    """No calibration data → q_hat = 1.0 (interval is the entire [0,1])."""
    assert split_quantile([], [], alpha=0.10) == 1.0


def test_split_quantile_alpha_validation():
    with pytest.raises(ValueError):
        split_quantile([0.5], [1], alpha=0.0)
    with pytest.raises(ValueError):
        split_quantile([0.5], [1], alpha=1.0)


def test_split_quantile_increasing_alpha_decreases_q_hat():
    """Wider miscoverage tolerance → narrower interval."""
    rng = random.Random(0)
    probs = [rng.random() for _ in range(200)]
    outcomes = [1 if rng.random() < p else 0 for p in probs]
    q_loose = split_quantile(probs, outcomes, alpha=0.30)
    q_tight = split_quantile(probs, outcomes, alpha=0.05)
    assert q_loose <= q_tight


def test_interval_bounds_clamped_to_unit():
    """p near 0 + large q_hat → lower bound clamps at 0."""
    ci = interval(p=0.05, q_hat=0.20, alpha=0.10)
    assert ci.p_lo == 0.0
    assert ci.p_hi == pytest.approx(0.25)
    ci2 = interval(p=0.95, q_hat=0.20, alpha=0.10)
    assert ci2.p_hi == 1.0
    assert ci2.p_lo == pytest.approx(0.75)


def test_interval_width_property():
    ci = interval(p=0.50, q_hat=0.10, alpha=0.10)
    assert ci.width == pytest.approx(0.20)


def test_coverage_guarantee_holds_in_practice():
    """On a calibrated random sample, the interval covers the outcome
    at least (1 - α) of the time, with finite-sample slack."""
    rng = random.Random(1)
    n_cal = 400
    cal_probs = [rng.random() for _ in range(n_cal)]
    cal_outcomes = [1 if rng.random() < p else 0 for p in cal_probs]

    n_test = 1000
    test_probs = [rng.random() for _ in range(n_test)]
    test_outcomes = [1 if rng.random() < p else 0 for p in test_probs]

    alpha = 0.10
    cis = fit_intervals(cal_probs, cal_outcomes, test_probs, alpha=alpha)
    # An outcome "falls in the interval" if the implied range is
    # non-empty for the realised binary. For binary outcomes the
    # check is: the interval must straddle the value (0 or 1), or
    # contain the corresponding side. We check the simpler version
    # mandated by conformal theory: |p - y| <= q_hat.
    q_hat = cis[0].q_hat
    n_covered = sum(1 for p, y in zip(test_probs, test_outcomes) if abs(p - y) <= q_hat)
    coverage = n_covered / n_test
    # Allow finite-sample slack of 5pp below the nominal target.
    assert coverage >= (1 - alpha) - 0.05


def test_adaptive_quantile_basic_behavior():
    """Adaptive quantile is well-defined and within sensible bounds."""
    rng = random.Random(2)
    probs = [rng.random() for _ in range(300)]
    outcomes = [1 if rng.random() < p else 0 for p in probs]
    q = adaptive_quantile(probs, outcomes, alpha=0.10, half_life=50)
    assert 0.0 <= q <= 1.0


def test_adaptive_quantile_diverges_when_recent_data_differs():
    """When recent calibration data has narrower errors than old, the
    adaptive quantile should reflect that — smaller than the static."""
    # Old errors: large (random predictions vs random outcomes).
    rng = random.Random(3)
    old_probs = [rng.random() for _ in range(200)]
    old_outcomes = [1 if rng.random() < 0.5 else 0 for _ in range(200)]
    # New errors: tiny (very accurate predictions).
    new_probs = [rng.random() for _ in range(200)]
    new_outcomes = [1 if rng.random() < p else 0 for p in new_probs]
    # Make new errors *deliberately small* by aligning predictions
    # very close to outcomes.
    new_probs = [
        (0.95 if o == 1 else 0.05) for o in new_outcomes
    ]

    all_probs = old_probs + new_probs
    all_outcomes = old_outcomes + new_outcomes

    q_static = split_quantile(all_probs, all_outcomes, alpha=0.10)
    q_adaptive = adaptive_quantile(all_probs, all_outcomes, alpha=0.10, half_life=50)
    # Adaptive weights recent (tight) data more — should produce a
    # smaller quantile.
    assert q_adaptive < q_static


def test_conservative_kelly_p_yes_returns_lower_bound():
    ci = interval(p=0.70, q_hat=0.05, alpha=0.10)
    assert conservative_kelly_p(ci, "YES") == pytest.approx(0.65)


def test_conservative_kelly_p_no_returns_lower_bound_of_complement():
    """For a NO trade, conservative p is 1 - p_hi of the YES side."""
    ci = interval(p=0.30, q_hat=0.05, alpha=0.10)
    # p_hi = 0.35, so 1 - p_hi = 0.65 — the conservative NO-side probability.
    assert conservative_kelly_p(ci, "NO") == pytest.approx(0.65)


def test_conservative_kelly_p_unknown_direction_raises():
    ci = interval(p=0.5, q_hat=0.05, alpha=0.10)
    with pytest.raises(ValueError):
        conservative_kelly_p(ci, "SOMEWHERE")


def test_fit_intervals_returns_one_per_test_prob():
    cis = fit_intervals(
        cal_probs=[0.2, 0.5, 0.8],
        cal_outcomes=[0, 1, 1],
        test_probs=[0.3, 0.6, 0.9],
        alpha=0.20,
    )
    assert len(cis) == 3
    # All intervals share the same q_hat from the calibration set.
    qs = {ci.q_hat for ci in cis}
    assert len(qs) == 1
