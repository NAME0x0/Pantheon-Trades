"""Trend feature — how strong is the recent directional move on this market.

We take a series of price snapshots (oldest first), compute the slope of a
simple linear regression on the log-price, and squash by a baseline slope
into [0, 1]. A flat series returns 0.5; a strong uptrend returns near 1;
a strong downtrend returns near 0.
"""

from __future__ import annotations

import math


BASELINE_SLOPE = 0.05  # ~5% per period; tuned for daily snapshots


def trend_score(prices: list[float] | None = None) -> float:
    if not prices or len(prices) < 3:
        return 0.5  # not enough data
    # Filter non-positive prices to allow log.
    series = [max(1e-6, p) for p in prices]
    n = len(series)
    xs = list(range(n))
    log_p = [math.log(p) for p in series]
    mean_x = sum(xs) / n
    mean_y = sum(log_p) / n
    num = sum((xs[i] - mean_x) * (log_p[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return 0.5
    slope = num / den
    # Map slope to [0, 1] via shifted sigmoid.
    z = slope / BASELINE_SLOPE
    return round(1.0 / (1.0 + math.exp(-z)), 6)
