"""Band classification — turn raw feature scores into a tradeable shortlist.

We score each candidate signal on six axes (edge magnitude, liquidity,
catalyst, sentiment, trend, correlation) and produce a single composite in
[0, 1]. The composite plus the absolute edge and liquidity floor decide
which band (S/A/B/C/D) the signal lands in. Only S and A go to the council;
B/C/D are surfaced for backtesting and post-hoc analysis only.
"""

from __future__ import annotations

from dataclasses import dataclass


BAND_THRESHOLDS: dict[str, dict[str, float]] = {
    "S": {"min_edge": 0.15, "min_liquidity": 0.80, "min_composite": 0.85},
    "A": {"min_edge": 0.08, "min_liquidity": 0.60, "min_composite": 0.70},
    "B": {"min_edge": 0.05, "min_liquidity": 0.40, "min_composite": 0.55},
    "C": {"min_edge": 0.02, "min_liquidity": 0.20, "min_composite": 0.40},
}

BAND_WEIGHTS: dict[str, float] = {
    "edge_abs_normalized": 0.35,
    "liquidity_score": 0.20,
    "catalyst_score": 0.15,
    "sentiment_score": 0.15,
    "trend_score": 0.10,
    "correlation_score": 0.05,
}

ELIGIBLE_BANDS: set[str] = {"S", "A"}

# Edge magnitudes above this saturate the edge-normalised contribution.
MAX_EDGE_FOR_NORMALIZATION = 0.30


@dataclass(frozen=True)
class BandResult:
    band: str
    composite: float
    eligible: bool


def compute_band_score(
    edge_abs: float,
    liquidity_score: float,
    catalyst_score: float,
    sentiment_score: float,
    trend_score: float,
    correlation_score: float,
    max_edge: float = MAX_EDGE_FOR_NORMALIZATION,
) -> float:
    edge_abs_normalized = min(max(edge_abs, 0.0) / max_edge, 1.0)
    composite = (
        BAND_WEIGHTS["edge_abs_normalized"] * edge_abs_normalized
        + BAND_WEIGHTS["liquidity_score"] * _clamp01(liquidity_score)
        + BAND_WEIGHTS["catalyst_score"] * _clamp01(catalyst_score)
        + BAND_WEIGHTS["sentiment_score"] * _clamp01(sentiment_score)
        + BAND_WEIGHTS["trend_score"] * _clamp01(trend_score)
        + BAND_WEIGHTS["correlation_score"] * _clamp01(correlation_score)
    )
    return round(composite, 6)


def classify_band(edge_abs: float, liquidity_score: float, composite_score: float) -> str:
    for band in ("S", "A", "B", "C"):
        t = BAND_THRESHOLDS[band]
        if (
            edge_abs >= t["min_edge"]
            and liquidity_score >= t["min_liquidity"]
            and composite_score >= t["min_composite"]
        ):
            return band
    return "D"


def classify(
    edge_abs: float,
    liquidity_score: float,
    catalyst_score: float,
    sentiment_score: float,
    trend_score: float,
    correlation_score: float,
) -> BandResult:
    composite = compute_band_score(
        edge_abs,
        liquidity_score,
        catalyst_score,
        sentiment_score,
        trend_score,
        correlation_score,
    )
    band = classify_band(edge_abs, liquidity_score, composite)
    return BandResult(band=band, composite=composite, eligible=band in ELIGIBLE_BANDS)


def is_eligible_for_boule(band: str) -> bool:
    return band in ELIGIBLE_BANDS


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v
