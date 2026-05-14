from __future__ import annotations

from datetime import datetime, timezone

from apollo.features.catalyst import CatalystEvent
from apollo.features.sentiment import SentimentSample
from apollo.scorer import MarketSnapshot, score_market


def _snap(**overrides) -> MarketSnapshot:
    base = dict(
        market_id="0xtest",
        question="Will X happen by 2026-12-31?",
        category="crypto",
        market_probability=0.40,
        bid=0.39,
        ask=0.41,
        volume_24h=200_000,
        open_interest=400_000,
        price_history=[0.30, 0.32, 0.35, 0.38, 0.40],
        price_std_24h=0.04,
        price_mean=0.40,
        catalysts=[CatalystEvent(description="rate decision", hours_until=24, relevance=0.8)],
        sentiment_samples=[SentimentSample(polarity=0.6, weight=2.0)],
        data_sources=["polymarket", "coingecko"],
        snapshot_at=datetime.now(timezone.utc),
        staleness_seconds=15,
        source_trust_score=0.9,
        days_to_resolution=14.0,
        sentiment_adjustment=0.05,
        trend_adjustment=0.03,
        catalyst_adjustment=0.04,
    )
    base.update(overrides)
    return MarketSnapshot(**base)


def test_score_market_produces_signal():
    sig = score_market(_snap())
    assert sig.market_id == "0xtest"
    assert 0.0 <= sig.market_probability <= 1.0
    assert 0.0 <= sig.oracle_probability <= 1.0
    assert sig.edge_abs == abs(sig.edge)


def test_score_market_band_eligibility_consistent():
    sig = score_market(_snap())
    if sig.band in ("S", "A"):
        assert sig.band_score >= 0.70
