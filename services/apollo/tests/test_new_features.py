"""Tests for the new Apollo features:
- geopolitical_risk (from GDELT)
- attention (from Wikipedia)
- macro_basis (from FRED)
- consensus_delta (from Manifold)
"""

from __future__ import annotations

import pytest

from apollo.features.attention import attention_score, compose as compose_attention
from apollo.features.consensus_delta import (
    WIDE_GAP_THRESHOLD,
    compose as compose_consensus,
    sizing_multiplier,
)
from apollo.features.geopolitical_risk import (
    directional_pressure,
    score as score_geo,
    tone_part,
    volume_part,
)
from apollo.features.macro_basis import compose as compose_macro, normalise_gap


# ─── Geopolitical risk ────────────────────────────────────────────────


def test_volume_part_zero_for_no_articles():
    assert volume_part(0) == 0.0


def test_volume_part_saturates_with_more_articles():
    """Monotonic and saturating below 1.0."""
    assert volume_part(50) < volume_part(150) < 1.0


def test_tone_part_neutral_when_none():
    assert tone_part(None) == 0.5


def test_tone_part_negative_tone_raises_risk():
    """Negative tone (-10) saturates risk part at 1.0."""
    assert tone_part(-10.0) == 1.0
    assert tone_part(-5.0) == 0.5
    assert tone_part(0.0) == 0.0
    assert tone_part(5.0) == 0.0


def test_score_combines_volume_and_tone():
    """High vol + very negative tone → risk near 1.0."""
    f = score_geo(country_or_theme="UA", article_count=300, average_tone=-15.0)
    assert f.risk_score > 0.9


def test_score_no_data_neutral_default():
    f = score_geo(country_or_theme="CH", article_count=0, average_tone=None)
    # vol_part=0, tone_part=0.5 → risk = 0.25
    assert 0.2 < f.risk_score < 0.3


def test_directional_pressure_signed_edge():
    """High risk vs low market_implied → positive edge."""
    out = directional_pressure(risk_score=0.80, market_implied=0.30)
    assert out["yes_bias"] == 0.80
    assert out["edge_signal"] == pytest.approx(0.50)


# ─── Attention ────────────────────────────────────────────────────────


def test_attention_score_neutral_when_none():
    assert attention_score(None) == 0.5


def test_attention_score_sigmoid_centered_at_zero():
    assert attention_score(0.0) == pytest.approx(0.5)
    # Sigmoid(z/2): z=2 ⇒ 1/(1+exp(-1)) ≈ 0.731
    assert attention_score(2.0) > 0.70
    assert attention_score(-2.0) < 0.30
    # Strong spike saturates
    assert attention_score(6.0) > 0.95
    assert attention_score(-6.0) < 0.05


def test_compose_attention_short_series_neutral():
    """Series too short to compute z → score 0.5."""
    f = compose_attention(article="X", series=[1, 2, 3], recent_days=3)
    assert f.score == 0.5
    assert f.velocity_z is None


def test_compose_attention_spike_detected():
    """Clear spike → high z, high score."""
    baseline = [100, 110, 95, 105, 98, 102, 99, 104, 96, 101, 100] * 3
    spike = [3000, 3500, 4000]
    f = compose_attention(article="X", series=baseline + spike, recent_days=3)
    assert f.velocity_z is not None
    assert f.velocity_z > 5
    assert f.score > 0.85


def test_compose_attention_flat_no_signal():
    """Flat series (zero variance) → undefined z → neutral score."""
    f = compose_attention(article="X", series=[100] * 30, recent_days=3)
    assert f.velocity_z is None
    assert f.score == 0.5


# ─── Macro basis ──────────────────────────────────────────────────────


def test_normalise_gap_within_unit_interval():
    """tanh squashes any gap to [-1, 1] — saturating allowed at the bounds."""
    for x in [-10, -1, 0, 1, 10]:
        out = normalise_gap(x, scale=0.5)
        assert -1.0 <= out <= 1.0
    # Small gap stays strictly interior
    assert -1.0 < normalise_gap(0.1, scale=0.5) < 1.0


def test_normalise_gap_zero_scale_safe():
    assert normalise_gap(5.0, scale=0.0) == 0.0


def test_compose_macro_missing_value_returns_none_bias():
    f = compose_macro(series_id="FEDFUNDS", latest_value=None, threshold=4.5, scale=0.25)
    assert f.yes_bias is None
    assert f.gap is None


def test_compose_macro_signed_gap_below_threshold():
    """latest 4.0 < threshold 4.5 → negative gap → negative bias."""
    f = compose_macro(series_id="FEDFUNDS", latest_value=4.0, threshold=4.5, scale=0.25)
    assert f.gap == pytest.approx(-0.5)
    assert f.yes_bias is not None
    assert f.yes_bias < 0


def test_compose_macro_bias_capped():
    """Extreme gap saturates at ±MAX_BIAS (0.30)."""
    f_hi = compose_macro(series_id="FOO", latest_value=10.0, threshold=0.0, scale=0.1)
    f_lo = compose_macro(series_id="FOO", latest_value=-10.0, threshold=0.0, scale=0.1)
    assert f_hi.yes_bias == pytest.approx(0.30, abs=1e-6)
    assert f_lo.yes_bias == pytest.approx(-0.30, abs=1e-6)


# ─── Consensus delta ──────────────────────────────────────────────────


def test_sizing_multiplier_small_gap_is_one():
    assert sizing_multiplier(0.0) == 1.0
    assert sizing_multiplier(0.04) == 1.0


def test_sizing_multiplier_wide_gap_floors_at_half():
    assert sizing_multiplier(0.20) == 0.5
    assert sizing_multiplier(-0.30) == 0.5


def test_sizing_multiplier_none_is_one():
    """No Manifold data → no effect on sizing."""
    assert sizing_multiplier(None) == 1.0


def test_sizing_multiplier_monotone_in_abs_delta():
    """Sizing multiplier strictly non-increasing as |delta| grows."""
    deltas = [0.0, 0.02, 0.05, 0.08, 0.10, 0.13, 0.15, 0.20]
    out = [sizing_multiplier(d) for d in deltas]
    assert all(out[i] >= out[i + 1] - 1e-9 for i in range(len(out) - 1))


def test_compose_consensus_no_manifold_data():
    f = compose_consensus(polymarket_p=0.42, manifold_p=None)
    assert f.manifold_p is None
    assert f.delta is None
    assert f.sizing_multiplier == 1.0


def test_compose_consensus_wide_disagreement_flag():
    f = compose_consensus(polymarket_p=0.30, manifold_p=0.50)
    assert f.delta == pytest.approx(0.20)
    assert f.abs_delta == pytest.approx(0.20)
    assert f.wide_disagreement is True
    assert f.sizing_multiplier == 0.5


def test_compose_consensus_minor_disagreement_keeps_full_sizing():
    f = compose_consensus(polymarket_p=0.42, manifold_p=0.44)
    assert f.wide_disagreement is False
    assert f.sizing_multiplier == 1.0


def test_wide_gap_threshold_value_matches_documented_constant():
    """Sanity: the constant is what we ship in docs."""
    assert WIDE_GAP_THRESHOLD == 0.15
