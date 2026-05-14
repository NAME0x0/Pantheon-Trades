"""Sentiment analyst — aggregate Reddit + news polarity into a single read."""

from __future__ import annotations


def sentiment_summary(samples: list[dict]) -> str:
    if not samples:
        return "no sentiment samples"
    total_weight = sum(float(s.get("weight", 1.0)) for s in samples)
    if total_weight <= 0:
        return "zero-weight samples"
    weighted = sum(float(s.get("polarity", 0.0)) * float(s.get("weight", 1.0)) for s in samples)
    mean = weighted / total_weight
    if mean > 0.2:
        label = "bullish"
    elif mean < -0.2:
        label = "bearish"
    else:
        label = "neutral"
    return f"{label} sentiment ({mean:+.2f} over {len(samples)} samples)"
