"""Attention-velocity feature from Wikipedia pageviews.

Wikipedia's per-article pageviews API exposes daily / hourly traffic
for any entity. A spike in pageviews vs the baseline window is a
documented investor-attention proxy ([Wiley 2024]). For prediction
markets whose underlying question has a Wikipedia article, the
z-score of recent vs baseline traffic is a leading indicator.

This module is pure math — Pythia's ``WikipediaSource`` supplies the
raw pageview series; we turn it into a unit-less score.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttentionFeature:
    article: str
    baseline_mean: float
    recent_mean: float
    velocity_z: float | None
    score: float  # 0..1 saturating monotone in velocity_z


def attention_score(velocity_z: float | None) -> float:
    """Map an attention z-score to [0, 1].

    Saturating sigmoid centred at z=0 with scale=2σ. A z of 2.0 maps
    to ~0.88; z=4 to ~0.98; z=0 to 0.50. Negative z (article losing
    attention) collapses toward 0.
    """
    if velocity_z is None:
        return 0.5  # no data ⇒ neutral
    # Sigmoid: 1 / (1 + exp(-z/2))
    import math
    return 1.0 / (1.0 + math.exp(-velocity_z / 2.0))


def compose(
    *,
    article: str,
    series: list[int],
    recent_days: int = 3,
) -> AttentionFeature:
    """Build the feature dataclass from a raw pageview series.

    ``series`` is daily counts (oldest first). ``recent_days`` slices
    the tail. Returns ``score = 0.5`` if the series is too short to
    compute a z.
    """
    if len(series) < recent_days + 1:
        return AttentionFeature(
            article=article, baseline_mean=0.0, recent_mean=0.0,
            velocity_z=None, score=0.5,
        )
    baseline = series[:-recent_days]
    recent = series[-recent_days:]
    mu = sum(baseline) / max(1, len(baseline))
    var = sum((x - mu) ** 2 for x in baseline) / max(1, len(baseline) - 1)
    sd = var ** 0.5
    recent_mean = sum(recent) / len(recent)
    z = (recent_mean - mu) / sd if sd > 0 else None
    return AttentionFeature(
        article=article,
        baseline_mean=mu,
        recent_mean=recent_mean,
        velocity_z=z,
        score=attention_score(z),
    )
