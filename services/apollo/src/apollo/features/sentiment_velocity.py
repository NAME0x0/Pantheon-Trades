"""Sentiment velocity — time-derivative of news polarity.

Absolute polarity is noisy. *Change* in polarity is what moves
markets — a market closing at 0.42 with rising news positivity is
more likely heading up than one with flat-but-positive sentiment.

We compute a simple weighted slope across an ordered list of
sentiment readings. Older readings get exponentially less weight so
fresh news dominates. The output is a probability delta capped at
``MAX_DELTA``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MAX_DELTA = 0.03
HALF_LIFE_SAMPLES = 4.0


@dataclass(frozen=True)
class SentimentTick:
    """One sentiment reading, ordered oldest → newest in the input list."""
    polarity: float    # [-1, +1]
    weight: float = 1.0  # source-trust × volume


def _weighted_slope(ticks: list[SentimentTick]) -> float:
    """Exponentially-weighted slope across ``ticks``.

    Returns a slope in roughly [-2, +2] (polarity is bounded, ticks
    are spaced uniformly so dt = 1 sample).
    """
    if len(ticks) < 2:
        return 0.0
    n = len(ticks)
    decay = math.log(2.0) / max(HALF_LIFE_SAMPLES, 0.5)
    # Exponential weights: most recent tick has weight 1, oldest has
    # weight exp(-decay * (n-1)).
    weights = [math.exp(-decay * (n - 1 - i)) * (t.weight or 1.0) for i, t in enumerate(ticks)]
    xs = list(range(n))
    ys = [t.polarity for t in ticks]
    sw = sum(weights)
    if sw <= 0:
        return 0.0
    mean_x = sum(w * x for w, x in zip(weights, xs)) / sw
    mean_y = sum(w * y for w, y in zip(weights, ys)) / sw
    cov = sum(w * (x - mean_x) * (y - mean_y) for w, x, y in zip(weights, xs, ys))
    var_x = sum(w * (x - mean_x) ** 2 for w, x in zip(weights, xs))
    if var_x <= 0:
        return 0.0
    return cov / var_x


def sentiment_velocity_probability_delta(
    ticks: list[SentimentTick],
    *,
    scale: float = MAX_DELTA,
) -> float:
    """Probability adjustment from the slope of recent sentiment.

    Rising sentiment → +delta. Falling sentiment → -delta. Flat → 0.
    """
    if len(ticks) < 2:
        return 0.0
    slope = _weighted_slope(ticks)
    # Slope is in polarity-units per sample. Compress with tanh so
    # extreme slopes don't blow past the cap.
    return float(scale * math.tanh(slope))
