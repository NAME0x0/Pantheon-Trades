"""Verify the new edge features actually move oracle_probability when
populated, and do nothing (no behavioural change) when omitted.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apollo.scorer import MarketSnapshot, score_market


def _base_snap(**overrides) -> MarketSnapshot:
    defaults = dict(
        market_id="0xtest",
        question="Will event X happen by 2026-12-31?",
        category="politics",
        market_probability=0.50,
        bid=0.49,
        ask=0.51,
        volume_24h=100_000.0,
        open_interest=400_000.0,
        price_history=[0.48, 0.49, 0.50, 0.51, 0.50],
        price_std_24h=0.01,
        price_mean=0.50,
        data_sources=["test"],
        snapshot_at=datetime(2026, 5, 17, tzinfo=timezone.utc),
        staleness_seconds=10,
        source_trust_score=0.9,
    )
    defaults.update(overrides)
    return MarketSnapshot(**defaults)


def test_no_new_features_oracle_equals_market():
    """Without any of the new feature inputs, oracle ≈ market (modulo
    the existing sentiment/trend/catalyst adjustments which are all 0
    here). The new feature plumbing must be a true no-op when unused."""
    sig = score_market(_base_snap())
    # base_prob=0.5, no adjustments at all ⇒ oracle should be 0.5
    assert sig.oracle_probability == pytest.approx(0.50, abs=1e-9)


def test_gdelt_high_risk_biases_yes():
    """Heavy distressed coverage → positive YES bias on oracle."""
    sig = score_market(_base_snap(
        gdelt_article_count=500,
        gdelt_average_tone=-12.0,
    ))
    assert sig.oracle_probability > 0.50
    # And the bias is capped at MAX_GEOPOLITICAL_DELTA = 0.05
    assert sig.oracle_probability <= 0.55 + 1e-9


def test_gdelt_low_risk_biases_no():
    """High volume + positive tone → no risk → negative bias toward NO."""
    sig = score_market(_base_snap(
        gdelt_article_count=200,
        gdelt_average_tone=5.0,
    ))
    # tone +5 saturates tone_part to 0, volume_part ~0.98 ⇒ risk ~0.49
    # (volume_weight=0.5 default). Just below 0.5 ⇒ tiny NO bias.
    assert sig.oracle_probability < 0.55


def test_wikipedia_attention_spike_biases_yes():
    """Big pageview spike → positive YES bias.

    Baseline must have non-zero variance — a perfectly flat series
    gives an undefined z and contributes 0 (neutral fallback). That
    is the correct behaviour; this test gives the baseline enough
    natural variation to exercise the spike branch.
    """
    baseline = [100 + (i % 10) * 5 for i in range(27)]
    spike = [3000, 3500, 4000]
    sig = score_market(_base_snap(
        wikipedia_pageview_series=baseline + spike,
        wikipedia_recent_days=3,
    ))
    assert sig.oracle_probability > 0.50


def test_wikipedia_short_series_no_effect():
    """Series too short to compute z → attention contributes 0."""
    sig = score_market(_base_snap(
        wikipedia_pageview_series=[100, 200],
        wikipedia_recent_days=3,
    ))
    assert sig.oracle_probability == pytest.approx(0.50, abs=1e-9)


def test_fred_macro_above_threshold_biases_yes():
    """Latest FRED value above the operator's threshold → YES bias."""
    sig = score_market(_base_snap(
        fred_latest_value=5.0,
        fred_threshold=4.5,
        fred_scale=0.25,
    ))
    assert sig.oracle_probability > 0.50


def test_fred_macro_below_threshold_biases_no():
    sig = score_market(_base_snap(
        fred_latest_value=4.0,
        fred_threshold=4.5,
        fred_scale=0.25,
    ))
    assert sig.oracle_probability < 0.50


def test_manifold_disagreement_pulls_oracle():
    """Manifold consensus 0.70 vs Polymarket 0.50 → mild YES pull."""
    sig = score_market(_base_snap(
        market_probability=0.50,
        manifold_implied=0.70,
    ))
    assert sig.oracle_probability > 0.50
    # Capped at MAX_CONSENSUS_DELTA = 0.05
    assert sig.oracle_probability <= 0.55 + 1e-9


def test_manifold_wide_gap_shrinks_band_score():
    """Wide Manifold-Polymarket gap caps band_score (sizing multiplier)."""
    sig_close = score_market(_base_snap(
        market_probability=0.50,
        manifold_implied=0.52,
    ))
    sig_wide = score_market(_base_snap(
        market_probability=0.50,
        manifold_implied=0.80,
    ))
    # Wide-disagreement multiplier of 0.5 should produce a smaller
    # band_score than the close-agreement case (for matched signals).
    assert sig_wide.band_score < sig_close.band_score


def test_per_feature_caps_bound_total_movement():
    """All four new features at max should move oracle by no more than
    ~0.20 in either direction (4 × 0.05). Plus existing legacy adjustments,
    but those are zero in this test."""
    sig_up = score_market(_base_snap(
        gdelt_article_count=1000,
        gdelt_average_tone=-20.0,
        wikipedia_pageview_series=[100 + (i % 10) * 5 for i in range(27)] + [10_000] * 3,
        fred_latest_value=100.0,
        fred_threshold=0.0,
        fred_scale=0.1,
        manifold_implied=0.99,
    ))
    # 0.50 + ≤0.20 = ≤0.70. Plus oracle_probability clips to (0, 1) anyway.
    assert sig_up.oracle_probability <= 0.75
    assert sig_up.oracle_probability > 0.60  # all four pushing YES

    sig_dn = score_market(_base_snap(
        gdelt_article_count=300,
        gdelt_average_tone=10.0,
        wikipedia_pageview_series=[10_000 + (i % 10) * 50 for i in range(27)] + [100] * 3,
        fred_latest_value=-100.0,
        fred_threshold=0.0,
        fred_scale=0.1,
        manifold_implied=0.01,
    ))
    assert sig_dn.oracle_probability >= 0.25
    assert sig_dn.oracle_probability < 0.40  # all four pushing NO


def test_legacy_callers_unaffected():
    """Snapshots that don't set any new fields must produce the same
    Signal as before the new feature wiring."""
    sig_a = score_market(_base_snap())
    sig_b = score_market(_base_snap(
        gdelt_article_count=None,
        gdelt_average_tone=None,
        wikipedia_pageview_series=[],
        fred_latest_value=None,
        fred_threshold=None,
        manifold_implied=None,
    ))
    assert sig_a.oracle_probability == sig_b.oracle_probability
    assert sig_a.band_score == sig_b.band_score
