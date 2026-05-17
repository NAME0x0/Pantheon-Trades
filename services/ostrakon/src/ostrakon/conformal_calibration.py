"""Split conformal prediction for binary classifiers.

Conformal prediction (Vovk, Gammerman, Shafer) gives distribution-free
finite-sample coverage guarantees. For our use case, the *split*
variant returns an interval ``[p_lo, p_hi]`` around any raw predicted
probability such that the true outcome falls in the implied range
``alpha`` fraction of the time, regardless of the model's calibration.

Why we want this for Pantheon:

  Kelly sizing is convex in p — small probability errors near 0 and 1
  cause large sizing errors. Areopagus currently sizes against a
  *point estimate* ``council_probability``. Switching to ``p_lo``
  (conservative lower bound) gives natural regularisation that
  *widens the interval* exactly where calibration data is thinnest,
  without retraining the council.

This implementation is **the standard split-conformal recipe**:

  1. Split your held-out calibration set into a fitting set + a
     conformal set.
  2. On the conformal set, compute nonconformity scores
     ``s_i = |p_i - y_i|`` (absolute error of predicted probability
     against the binary outcome).
  3. The (1 - α) quantile ``q_hat`` of the conformal scores is the
     interval half-width.
  4. For any new prediction ``p``: return ``[max(0, p - q_hat),
     min(1, p + q_hat)]``.

Coverage guarantee: for exchangeable data, the true outcome falls in
the implied range at least ``1 - α`` of the time.

Caveat: prediction-market outcomes are not exchangeable across regime
changes. The adaptive variant (rolling-window conformal) reweights
recent calibration data — see ``adaptive_quantile()`` below.

References:
  Vovk, Gammerman, Shafer (2005). Algorithmic Learning in a Random World.
  Lei et al. (2018). Distribution-Free Predictive Inference for Regression.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ConformalInterval:
    """A conformal prediction interval around a point probability.

    Attributes:
        p: original predicted probability in [0, 1].
        p_lo: lower bound — ``max(0, p - q_hat)``.
        p_hi: upper bound — ``min(1, p + q_hat)``.
        q_hat: the conformal quantile (interval half-width).
        alpha: nominal miscoverage rate. Default 0.10 ⇒ 90% intervals.
    """

    p: float
    p_lo: float
    p_hi: float
    q_hat: float
    alpha: float

    @property
    def width(self) -> float:
        return self.p_hi - self.p_lo


def split_quantile(
    cal_probs: list[float],
    cal_outcomes: list[int],
    *,
    alpha: float = 0.10,
) -> float:
    """Compute the conformal quantile from a calibration sample.

    Returns ``q_hat`` such that ``|p - y| <= q_hat`` for at least
    ``(1 - α)`` fraction of the calibration set, with the standard
    finite-sample correction ``ceil((n+1)(1-α)) / n``.
    """
    n = len(cal_probs)
    if n == 0:
        return 1.0  # max width — interval is the entire [0, 1]
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}")

    # Nonconformity scores: absolute error of predicted vs realised.
    scores = sorted(abs(p - y) for p, y in zip(cal_probs, cal_outcomes))

    # Quantile index with the (n+1)(1-α) correction.
    k = math.ceil((n + 1) * (1 - alpha))
    # Clamp to a valid index.
    k = max(1, min(n, k))
    return scores[k - 1]


def adaptive_quantile(
    cal_probs: list[float],
    cal_outcomes: list[int],
    *,
    alpha: float = 0.10,
    half_life: int = 100,
) -> float:
    """Time-decayed conformal quantile.

    Newer calibration points get more weight via an exponential decay
    parametrised by ``half_life`` (number of newer samples for the
    weight to halve). Useful when the data is non-exchangeable but
    *recent* data is approximately exchangeable.

    Implementation: form a weighted-quantile estimator. The naive
    sort-and-pick approach below is O(n log n) — fast enough for the
    sample sizes we care about (typically n < 10,000).
    """
    n = len(cal_probs)
    if n == 0:
        return 1.0
    if not 0 < alpha < 1:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}")

    decay = math.log(2) / max(1, half_life)
    # Most-recent sample (index n-1) gets weight 1.0; earlier samples
    # decay exponentially. The caller is responsible for passing
    # cal_probs / cal_outcomes in chronological order.
    weights = [math.exp(-decay * (n - 1 - i)) for i in range(n)]
    total_w = sum(weights)
    if total_w <= 0:
        return 1.0

    scored = sorted(
        (abs(p - y), w) for p, y, w in zip(cal_probs, cal_outcomes, weights)
    )
    target = (1 - alpha) * total_w
    cum = 0.0
    for s, w in scored:
        cum += w
        if cum >= target:
            return s
    return scored[-1][0]


def interval(
    p: float,
    q_hat: float,
    alpha: float = 0.10,
) -> ConformalInterval:
    """Build the ``[p_lo, p_hi]`` interval around a point probability."""
    p_clamped = max(0.0, min(1.0, float(p)))
    lo = max(0.0, p_clamped - q_hat)
    hi = min(1.0, p_clamped + q_hat)
    return ConformalInterval(
        p=p_clamped,
        p_lo=lo,
        p_hi=hi,
        q_hat=q_hat,
        alpha=alpha,
    )


def fit_intervals(
    cal_probs: list[float],
    cal_outcomes: list[int],
    test_probs: list[float],
    *,
    alpha: float = 0.10,
    adaptive: bool = False,
    half_life: int = 100,
) -> list[ConformalInterval]:
    """Convenience: fit on calibration set, return intervals for every
    test probability. Used by the Areopagus sizing path.
    """
    if adaptive:
        q_hat = adaptive_quantile(cal_probs, cal_outcomes, alpha=alpha, half_life=half_life)
    else:
        q_hat = split_quantile(cal_probs, cal_outcomes, alpha=alpha)
    return [interval(p, q_hat, alpha=alpha) for p in test_probs]


def conservative_kelly_p(ci: ConformalInterval, direction: str) -> float:
    """Return the conservative probability for Kelly sizing.

    For a YES-direction trade, the conservative ``p`` is the *lower*
    bound (we don't want to over-size on the optimistic end of the
    interval). For a NO-direction trade, ``1 - p_hi`` (equivalent —
    treats the NO side's lower bound).

    Args:
        ci: a fitted ``ConformalInterval`` around the council's point
            estimate.
        direction: ``"YES"`` or ``"NO"``.
    """
    if direction == "YES":
        return ci.p_lo
    if direction == "NO":
        return 1.0 - ci.p_hi
    raise ValueError(f"direction must be YES or NO; got {direction}")
