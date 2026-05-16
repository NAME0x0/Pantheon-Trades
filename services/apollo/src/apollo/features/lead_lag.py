"""Lead/lag cross-market correlation feature.

When a market is correlated with another — say a Polymarket "will BTC
close above $120k" market and the Coinbase BTC perp — moves in the
faster venue precede moves in the slower venue. If the leader has
moved up in the last N minutes and our prediction market hasn't yet,
that's expected upward pressure.

The function takes paired price series and computes:

  1. The maximum cross-correlation across a small set of lags.
  2. The price-move delta on the leader since the lag horizon.
  3. The expected follower move = leader_move × correlation.
  4. A capped probability delta in roughly [-0.05, +0.05].

If there is no correlation > ``MIN_CORR`` at any lag, the feature
returns 0 — never inject signal where there isn't one.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

MAX_DELTA = 0.05
MIN_CORR = 0.3


@dataclass(frozen=True)
class LeadLagSnapshot:
    leader_id: str
    leader_series: list[float]    # price series, oldest → newest
    follower_series: list[float]  # this market's price series, same cadence
    horizons: tuple[int, ...] = (1, 3, 5, 10)  # lags to test (samples)


def _pearson(a: list[float], b: list[float]) -> float:
    if len(a) < 3 or len(a) != len(b):
        return 0.0
    try:
        mean_a = statistics.fmean(a)
        mean_b = statistics.fmean(b)
        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
        var_a = sum((x - mean_a) ** 2 for x in a)
        var_b = sum((y - mean_b) ** 2 for y in b)
        if var_a <= 0 or var_b <= 0:
            return 0.0
        return cov / ((var_a ** 0.5) * (var_b ** 0.5))
    except (statistics.StatisticsError, ValueError):
        return 0.0


def best_lag(snap: LeadLagSnapshot) -> tuple[int, float]:
    """Search the lag horizons for the strongest leader→follower correlation.

    Returns (lag, correlation). Lag is the number of samples the leader
    leads by. Correlation can be negative (leader inversely predicts).
    """
    leader = snap.leader_series
    follower = snap.follower_series
    n = min(len(leader), len(follower))
    if n < max(snap.horizons) + 3:
        return 0, 0.0
    best = (0, 0.0)
    for lag in snap.horizons:
        # leader[t - lag] aligned with follower[t]
        a = leader[: n - lag]
        b = follower[lag:n]
        if len(a) != len(b) or not a:
            continue
        r = _pearson(a, b)
        if abs(r) > abs(best[1]):
            best = (lag, r)
    return best


def lead_lag_probability_delta(snap: LeadLagSnapshot, *, scale: float = MAX_DELTA) -> float:
    """Convert the leader's recent move into a probability adjustment.

    Mechanics:
      1. Pick the best lag + correlation.
      2. Measure the leader's price move over that lag.
      3. Expected follower move = leader_move × correlation.
      4. Convert to a probability delta capped at ``scale``.
    """
    lag, corr = best_lag(snap)
    if abs(corr) < MIN_CORR or lag <= 0:
        return 0.0
    leader = snap.leader_series
    if len(leader) <= lag:
        return 0.0
    # Recent move in the leader over the chosen lag.
    leader_move = leader[-1] - leader[-1 - lag]
    expected = leader_move * corr
    # Clip to [-scale, +scale]. The raw `expected` is in the same units
    # as the leader's series; we treat it as a probability delta after
    # signing because both series are in the [0,1] probability domain
    # (Polymarket-style) or normalised to it by the caller.
    return float(max(-scale, min(scale, expected)))
