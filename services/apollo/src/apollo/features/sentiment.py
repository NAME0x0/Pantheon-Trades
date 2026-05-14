"""Sentiment feature — directional pressure from news + Reddit.

We collapse a list of weighted polarity samples in [-1, +1] (negative =
bearish on the YES outcome, positive = bullish) into a single score in
[0, 1] where 0.5 is neutral. Samples are weighted by source trust; the
mean polarity is mapped into [0, 1] by ``(mean + 1) / 2``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentSample:
    polarity: float  # in [-1, +1]
    weight: float = 1.0  # source trust / volume


def sentiment_score(samples: list[SentimentSample] | None = None) -> float:
    if not samples:
        return 0.5  # neutral when blind
    total_w = 0.0
    weighted_polarity = 0.0
    for s in samples:
        w = max(s.weight, 0.0)
        if w == 0:
            continue
        polarity = max(-1.0, min(1.0, s.polarity))
        weighted_polarity += polarity * w
        total_w += w
    if total_w == 0:
        return 0.5
    mean = weighted_polarity / total_w
    return round((mean + 1.0) / 2.0, 6)
