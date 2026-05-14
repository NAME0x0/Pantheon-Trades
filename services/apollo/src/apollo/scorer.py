"""Apollo signal scorer — turns a Pythia market snapshot into a typed Signal.

Inputs are intentionally narrow: every adapter from Pythia projects its raw
payload into a ``MarketSnapshot`` before reaching the scorer, so this module
only has to do math, not source-specific parsing. The scorer applies edge
calculation, band classification, and assembles the final ``Signal`` model
that downstream services consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pantheon_core.schema import Signal, utc_now

from apollo.bands import classify
from apollo.features.catalyst import CatalystEvent, catalyst_score
from apollo.features.correlation import correlation_score
from apollo.features.edge import compute_edge, oracle_probability
from apollo.features.liquidity import liquidity_score
from apollo.features.sentiment import SentimentSample, sentiment_score
from apollo.features.trend import trend_score
from apollo.features.volatility import volatility_score


@dataclass
class MarketSnapshot:
    """Normalised input record built by Pythia adapters."""

    market_id: str
    question: str
    category: Literal["crypto", "politics", "sports", "science", "other"]

    market_probability: float
    bid: float
    ask: float
    volume_24h: float
    open_interest: float

    # Time series and contextual features.
    price_history: list[float] = field(default_factory=list)
    price_std_24h: float = 0.0
    price_mean: float = 0.0

    catalysts: list[CatalystEvent] = field(default_factory=list)
    sentiment_samples: list[SentimentSample] = field(default_factory=list)
    open_position_correlations: list[float] = field(default_factory=list)

    # Pythia adapter context.
    data_sources: list[str] = field(default_factory=list)
    snapshot_at: datetime = field(default_factory=utc_now)
    staleness_seconds: int = 0
    source_trust_score: float = 1.0
    resolution_date: datetime | None = None
    days_to_resolution: float | None = None

    # Calibration deltas in probability space (typically -0.1..+0.1 each).
    sentiment_adjustment: float = 0.0
    trend_adjustment: float = 0.0
    catalyst_adjustment: float = 0.0
    calibration_factor: float = 1.0


def score_market(snap: MarketSnapshot) -> Signal:
    """Score a single ``MarketSnapshot`` into a downstream-ready ``Signal``."""
    spread = max(0.0, snap.ask - snap.bid)
    liq = liquidity_score(snap.volume_24h, snap.open_interest, spread)
    vol = volatility_score(snap.price_std_24h, snap.price_mean) if snap.price_mean else 0.0
    cat = catalyst_score(snap.catalysts)
    sent = sentiment_score(snap.sentiment_samples)
    trnd = trend_score(snap.price_history)
    corr = correlation_score(snap.open_position_correlations)

    oracle_p = oracle_probability(
        base_prob=snap.market_probability,
        sentiment_adj=snap.sentiment_adjustment,
        trend_adj=snap.trend_adjustment,
        catalyst_adj=snap.catalyst_adjustment,
        calibration_factor=snap.calibration_factor,
    )
    edge, edge_abs = compute_edge(oracle_p, snap.market_probability)

    band_result = classify(edge_abs, liq, cat, sent, trnd, corr)

    return Signal(
        market_id=snap.market_id,
        question=snap.question,
        category=snap.category,
        market_probability=snap.market_probability,
        oracle_probability=oracle_p,
        edge=edge,
        edge_abs=edge_abs,
        band=band_result.band,  # type: ignore[arg-type]
        band_score=band_result.composite,
        liquidity_score=liq,
        volatility_score=vol,
        catalyst_score=cat,
        sentiment_score=sent,
        correlation_score=corr,
        trend_score=trnd,
        volume_24h=snap.volume_24h,
        open_interest=snap.open_interest,
        bid=snap.bid,
        ask=snap.ask,
        spread=spread,
        resolution_date=snap.resolution_date,
        days_to_resolution=snap.days_to_resolution,
        data_sources=snap.data_sources,
        staleness_seconds=snap.staleness_seconds,
        source_trust_score=snap.source_trust_score,
        pythia_snapshot_at=snap.snapshot_at,
    )
