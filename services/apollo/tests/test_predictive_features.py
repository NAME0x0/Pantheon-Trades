"""Tests for the three Tier 2 predictive feature primitives."""

from __future__ import annotations


from apollo.features.lead_lag import LeadLagSnapshot, lead_lag_probability_delta, best_lag
from apollo.features.orderbook_imbalance import (
    OrderBookLevel,
    imbalance_probability_delta,
    orderbook_imbalance,
)
from apollo.features.sentiment_velocity import (
    SentimentTick,
    sentiment_velocity_probability_delta,
)


# ─── Order-book imbalance ──────────────────────────────────────────────


def test_balanced_book_yields_zero():
    bids = [OrderBookLevel(0.42, 1000), OrderBookLevel(0.41, 500)]
    asks = [OrderBookLevel(0.43, 1000), OrderBookLevel(0.44, 500)]
    assert abs(orderbook_imbalance(bids, asks)) < 1e-6
    assert abs(imbalance_probability_delta(bids, asks)) < 1e-6


def test_bid_heavy_pushes_up():
    bids = [OrderBookLevel(0.42, 5000)]
    asks = [OrderBookLevel(0.43, 500)]
    delta = imbalance_probability_delta(bids, asks)
    assert delta > 0
    assert delta <= 0.04 + 1e-6


def test_ask_heavy_pushes_down():
    bids = [OrderBookLevel(0.42, 500)]
    asks = [OrderBookLevel(0.43, 5000)]
    delta = imbalance_probability_delta(bids, asks)
    assert delta < 0
    assert delta >= -0.04 - 1e-6


def test_empty_book_safe():
    assert orderbook_imbalance([], []) == 0.0
    assert imbalance_probability_delta([], []) == 0.0


def test_only_inside_window_counts():
    bids = [
        OrderBookLevel(0.42, 100),    # at top
        OrderBookLevel(0.30, 10_000), # far below — should be excluded
    ]
    asks = [OrderBookLevel(0.43, 100)]
    # window_pp=0.03 → deep bid excluded → roughly balanced.
    delta = imbalance_probability_delta(bids, asks, window_pp=0.03)
    assert abs(delta) < 0.02


# ─── Lead/lag ─────────────────────────────────────────────────────────


def test_perfectly_correlated_follower_responds():
    leader = [0.40, 0.42, 0.45, 0.48, 0.50, 0.52, 0.55, 0.58, 0.60, 0.62, 0.65, 0.68]
    # Follower is the same series shifted by 2 samples (leader leads by 2).
    follower = [0.40, 0.40] + leader[:-2]
    snap = LeadLagSnapshot("BTC-perp", leader, follower, horizons=(1, 2, 3, 5))
    lag, corr = best_lag(snap)
    assert lag >= 1
    assert corr > 0.5
    delta = lead_lag_probability_delta(snap)
    # Leader has been rising — positive delta.
    assert delta > 0


def test_low_correlation_yields_zero_delta():
    leader = [0.5] * 12
    follower = [0.4, 0.6, 0.3, 0.7, 0.5, 0.8, 0.4, 0.5, 0.6, 0.5, 0.4, 0.3]
    snap = LeadLagSnapshot("noise", leader, follower)
    assert lead_lag_probability_delta(snap) == 0.0


def test_short_series_returns_zero():
    leader = [0.5, 0.6]
    follower = [0.5, 0.6]
    snap = LeadLagSnapshot("short", leader, follower)
    assert lead_lag_probability_delta(snap) == 0.0


def test_capped_at_max_delta():
    # Huge leader move with near-perfect correlation — must still cap.
    leader = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    follower = [0.1, 0.1, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    snap = LeadLagSnapshot("big", leader, follower, horizons=(1, 2, 3))
    delta = lead_lag_probability_delta(snap)
    assert abs(delta) <= 0.05 + 1e-6


# ─── Sentiment velocity ───────────────────────────────────────────────


def test_rising_sentiment_positive_delta():
    ticks = [
        SentimentTick(polarity=-0.4),
        SentimentTick(polarity=-0.1),
        SentimentTick(polarity=0.2),
        SentimentTick(polarity=0.5),
        SentimentTick(polarity=0.7),
    ]
    delta = sentiment_velocity_probability_delta(ticks)
    assert delta > 0


def test_falling_sentiment_negative_delta():
    ticks = [
        SentimentTick(polarity=0.7),
        SentimentTick(polarity=0.4),
        SentimentTick(polarity=0.0),
        SentimentTick(polarity=-0.3),
        SentimentTick(polarity=-0.5),
    ]
    delta = sentiment_velocity_probability_delta(ticks)
    assert delta < 0


def test_flat_sentiment_zero_delta():
    ticks = [SentimentTick(polarity=0.3) for _ in range(5)]
    delta = sentiment_velocity_probability_delta(ticks)
    assert abs(delta) < 1e-3


def test_single_tick_zero():
    assert sentiment_velocity_probability_delta([SentimentTick(0.5)]) == 0.0
    assert sentiment_velocity_probability_delta([]) == 0.0


def test_velocity_capped():
    # Extreme polarity swing — delta still capped.
    ticks = [SentimentTick(polarity=-1.0), SentimentTick(polarity=1.0)] * 5
    delta = sentiment_velocity_probability_delta(ticks)
    assert abs(delta) <= 0.03 + 1e-6
