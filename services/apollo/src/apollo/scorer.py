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
from apollo.features.attention import compose as attention_compose
from apollo.features.catalyst import CatalystEvent, catalyst_score
from apollo.features.consensus_delta import compose as consensus_compose
from apollo.features.correlation import correlation_score
from apollo.features.edge import compute_edge, oracle_probability
from apollo.features.geopolitical_risk import score as geopolitical_score
from apollo.features.lead_lag import LeadLagSnapshot, lead_lag_probability_delta
from apollo.features.liquidity import liquidity_score
from apollo.features.macro_basis import compose as macro_compose
from apollo.features.orderbook_imbalance import (
    OrderBookLevel,
    imbalance_probability_delta,
)
from apollo.features.sentiment import SentimentSample, sentiment_score
from apollo.features.sentiment_velocity import (
    SentimentTick,
    sentiment_velocity_probability_delta,
)
from apollo.features.trend import trend_score
from apollo.features.volatility import volatility_score

# Per-feature contribution caps for the new edge sources. Each feature
# can move the oracle probability by at most ±MAX_*_DELTA. The total
# contribution from all four new features is therefore bounded at
# ±0.20 — large enough to be useful, small enough that one source's
# bad day cannot dominate the council's prior.
MAX_GEOPOLITICAL_DELTA = 0.05
MAX_ATTENTION_DELTA = 0.05
MAX_MACRO_DELTA = 0.05
MAX_CONSENSUS_DELTA = 0.05


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

    # ── Predictive features (Tier 2 alpha primitives) ──────────────
    # Order-book depth ladders, lead/lag price-series pairs, and
    # time-ordered sentiment ticks for the velocity feature. All
    # default to empty so legacy callers remain valid; populated
    # by Pythia adapters when the source actually carries the data.
    orderbook_bids: list[OrderBookLevel] = field(default_factory=list)
    orderbook_asks: list[OrderBookLevel] = field(default_factory=list)
    lead_lag_snapshots: list[LeadLagSnapshot] = field(default_factory=list)
    sentiment_ticks: list[SentimentTick] = field(default_factory=list)

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

    # ── New edge-source inputs (GDELT / Wikipedia / FRED / Manifold) ──
    # All optional — each Pythia adapter is expected to populate the
    # subset relevant to the market category. Apollo's scorer folds
    # them into oracle_probability with per-source contribution caps.
    #
    # GDELT geopolitical risk:
    gdelt_article_count: int | None = None
    gdelt_average_tone: float | None = None
    #
    # Wikipedia pageview-attention z-score:
    wikipedia_pageview_series: list[int] = field(default_factory=list)
    wikipedia_recent_days: int = 3
    #
    # FRED macro release vs an operator-supplied threshold:
    fred_latest_value: float | None = None
    fred_threshold: float | None = None
    fred_scale: float = 0.25
    #
    # Manifold consensus (free human prior for cross-check):
    manifold_implied: float | None = None


def score_market(snap: MarketSnapshot) -> Signal:
    """Score a single ``MarketSnapshot`` into a downstream-ready ``Signal``."""
    spread = max(0.0, snap.ask - snap.bid)
    liq = liquidity_score(snap.volume_24h, snap.open_interest, spread)
    vol = volatility_score(snap.price_std_24h, snap.price_mean) if snap.price_mean else 0.0
    cat = catalyst_score(snap.catalysts)
    sent = sentiment_score(snap.sentiment_samples)
    trnd = trend_score(snap.price_history)
    corr = correlation_score(snap.open_position_correlations)

    # Predictive deltas — each capped at its own MAX_DELTA so no single
    # primitive can dominate the oracle probability.
    imbalance_delta = (
        imbalance_probability_delta(snap.orderbook_bids, snap.orderbook_asks)
        if snap.orderbook_bids and snap.orderbook_asks
        else 0.0
    )
    leadlag_delta = 0.0
    for ll in snap.lead_lag_snapshots:
        leadlag_delta += lead_lag_probability_delta(ll)
    leadlag_delta = max(-0.05, min(0.05, leadlag_delta))
    velocity_delta = (
        sentiment_velocity_probability_delta(snap.sentiment_ticks)
        if len(snap.sentiment_ticks) >= 2
        else 0.0
    )

    # ── New edge-feature deltas ──────────────────────────────────────
    # Each new feature contributes a bounded probability delta. When
    # the relevant Pythia inputs are missing, the contribution is 0 —
    # i.e. legacy callers see identical behaviour to the prior scorer.

    geo_delta = 0.0
    if snap.gdelt_article_count is not None:
        geo = geopolitical_score(
            country_or_theme=snap.market_id,
            article_count=int(snap.gdelt_article_count),
            average_tone=snap.gdelt_average_tone,
        )
        # geo.risk_score ∈ [0, 1]; centred at 0.5 means "no info".
        # Map (risk - 0.5) → ±MAX delta. Convention: high risk →
        # YES bias on "bad thing happens" markets (Apollo's default
        # framing for geopolitics + world-event categories).
        geo_delta = max(-MAX_GEOPOLITICAL_DELTA, min(MAX_GEOPOLITICAL_DELTA,
            (geo.risk_score - 0.5) * 2.0 * MAX_GEOPOLITICAL_DELTA))

    attention_delta = 0.0
    if snap.wikipedia_pageview_series:
        attn = attention_compose(
            article=snap.market_id,
            series=snap.wikipedia_pageview_series,
            recent_days=snap.wikipedia_recent_days,
        )
        if attn.velocity_z is not None:
            # Spiking attention → mild YES bias on "thing happens"
            # markets. Sigmoid score - 0.5 is already centred.
            attention_delta = max(-MAX_ATTENTION_DELTA, min(MAX_ATTENTION_DELTA,
                (attn.score - 0.5) * 2.0 * MAX_ATTENTION_DELTA))

    macro_delta = 0.0
    if snap.fred_latest_value is not None and snap.fred_threshold is not None:
        macro = macro_compose(
            series_id=snap.market_id,
            latest_value=snap.fred_latest_value,
            threshold=snap.fred_threshold,
            scale=snap.fred_scale,
        )
        if macro.yes_bias is not None:
            macro_delta = max(-MAX_MACRO_DELTA, min(MAX_MACRO_DELTA,
                macro.yes_bias * MAX_MACRO_DELTA / 0.30))  # rescale to ±MAX

    consensus_delta = 0.0
    consensus_sizing_multiplier = 1.0
    if snap.manifold_implied is not None:
        cd = consensus_compose(
            polymarket_p=snap.market_probability,
            manifold_p=snap.manifold_implied,
        )
        # The delta itself is a hint, capped. Manifold consensus moves
        # the oracle a fraction of the way toward the Manifold prior.
        if cd.delta is not None:
            consensus_delta = max(-MAX_CONSENSUS_DELTA, min(MAX_CONSENSUS_DELTA,
                cd.delta * 0.3))  # 30% pull toward Manifold, capped
        consensus_sizing_multiplier = cd.sizing_multiplier

    # Fold the predictive adjustments into the existing sentiment /
    # trend envelope. oracle_probability still clips to (0, 1).
    sentiment_total = snap.sentiment_adjustment + velocity_delta + attention_delta
    trend_total = snap.trend_adjustment + leadlag_delta + imbalance_delta + geo_delta + macro_delta + consensus_delta

    oracle_p = oracle_probability(
        base_prob=snap.market_probability,
        sentiment_adj=sentiment_total,
        trend_adj=trend_total,
        catalyst_adj=snap.catalyst_adjustment,
        calibration_factor=snap.calibration_factor,
    )
    edge, edge_abs = compute_edge(oracle_p, snap.market_probability)

    # Cross-venue wide-disagreement caps the effective edge for sizing
    # downstream. Areopagus consumes signal.edge_abs * (an internal
    # cap based on band score); we surface the consensus multiplier
    # via the band_score so it cascades automatically.
    band_result = classify(edge_abs, liq, cat, sent, trnd, corr)
    if consensus_sizing_multiplier < 1.0:
        # Mutate band_result in place — strictly reduces sizing influence.
        # The .composite field is what Areopagus reads.
        from dataclasses import replace as _replace
        try:
            band_result = _replace(band_result, composite=band_result.composite * consensus_sizing_multiplier)
        except TypeError:
            # band_result is not a dataclass — fall back to attribute mutation.
            band_result.composite = band_result.composite * consensus_sizing_multiplier

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
