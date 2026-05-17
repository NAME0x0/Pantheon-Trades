"""Geopolitical-risk feature scored from GDELT 2.0 events.

Apollo's existing band scorer rewards markets where catalyst pressure
is high. GDELT gives us a real-time pulse of *coverage volume* and
*tone* for any country / theme. The combination is a clean Apollo
feature for world-event + geopolitics + politics markets.

This module is *pure feature math* — no I/O. Pythia's ``GdeltSource``
hands us the volume + tone numbers; we turn those into a unit-less
``geopolitical_risk_score`` in ``[0, 1]``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class GeopoliticalRiskFeature:
    country_or_theme: str
    article_count: int
    average_tone: float | None
    volume_part: float
    tone_part: float
    risk_score: float


# Volume saturates at ~150 articles in the window. Beyond that the
# additional signal-per-article is negligible — large news cycles look
# the same as catastrophic news cycles in raw counts.
VOLUME_SATURATION_ANCHOR = 50.0

# Tone is GDELT's news-sentiment score in roughly [-100, +100], but
# realised values cluster in [-15, +5]. -10 saturates the negative
# half; +5 (or non-distressed coverage) collapses to 0.
TONE_NEG_SATURATION = 10.0


def volume_part(article_count: int) -> float:
    """Volume → [0, 1] via 1 - exp(-n / anchor). Saturates politely."""
    if article_count <= 0:
        return 0.0
    return 1.0 - math.exp(-article_count / VOLUME_SATURATION_ANCHOR)


def tone_part(average_tone: float | None) -> float:
    """Negative tone → high risk part. No data → neutral 0.5 prior."""
    if average_tone is None:
        return 0.5
    # Map -10 (very distressed) → 1.0, 0 → 0.0, anything positive → 0.0.
    return max(0.0, min(1.0, -average_tone / TONE_NEG_SATURATION))


def score(
    *,
    country_or_theme: str,
    article_count: int,
    average_tone: float | None,
    volume_weight: float = 0.5,
) -> GeopoliticalRiskFeature:
    """Compose the unit-less risk score.

    Default 50/50 weighting between volume saturation and tone severity.
    Operator can adjust ``volume_weight`` per market type — for
    economic-policy markets you might want tone-heavy; for war /
    crisis markets, volume-heavy.
    """
    vp = volume_part(article_count)
    tp = tone_part(average_tone)
    w = max(0.0, min(1.0, volume_weight))
    risk = w * vp + (1.0 - w) * tp
    return GeopoliticalRiskFeature(
        country_or_theme=country_or_theme,
        article_count=article_count,
        average_tone=average_tone,
        volume_part=vp,
        tone_part=tp,
        risk_score=round(risk, 4),
    )


def directional_pressure(
    risk_score: float,
    market_implied: float,
) -> dict[str, float]:
    """Translate the risk score into a market-direction signal.

    Convention: high risk = bad news = bias toward the BAD outcome of
    the binary question. The mapping from "risk" to "YES/NO bias" is
    market-specific — most world-event markets phrase YES as "the bad
    thing happens" (e.g. "Will there be a recession in 2026?"), in
    which case high risk biases YES.

    Returns ``{"yes_bias": float, "edge_signal": float}`` where
    ``edge_signal`` is the signed delta vs the current market price.
    """
    # No re-shaping — risk score IS the YES bias for "bad thing" markets.
    yes_bias = max(0.0, min(1.0, risk_score))
    edge = yes_bias - market_implied
    return {"yes_bias": yes_bias, "edge_signal": edge}
