"""Tests for the highest-S/N alpha features:
- basis_arb (cross-venue spread)
- perps_signal (Binance funding + OI)
- cot_positioning (CFTC speculator z)

Plus scorer integration verifying each new field moves oracle in the
expected direction and is properly bounded.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apollo.features.basis_arb import (
    MAX_BASIS_BIAS,
    basis_spread,
    bias_from_basis,
    compose as basis_compose,
)
from apollo.features.cot_positioning import (
    MAX_COT_BIAS,
    compose as cot_compose,
)
from apollo.features.perps_signal import (
    MAX_PERPS_BIAS,
    cascade_risk,
    compose as perps_compose,
)
from apollo.scorer import MarketSnapshot, score_market


# ─── Basis arb ────────────────────────────────────────────────────────


def test_basis_spread_signed():
    assert basis_spread(0.50, 0.55) == pytest.approx(0.05)
    assert basis_spread(0.55, 0.50) == pytest.approx(-0.05)


def test_basis_spread_none_when_no_venue():
    assert basis_spread(0.50, None) is None


def test_bias_from_basis_zero_inside_costs():
    """Spread below cost-of-trade contributes zero."""
    # cost_pp = (500 + 50) / 10_000 = 0.055. Spread 0.04 < 0.055.
    assert bias_from_basis(0.04, fees_bps=500, slippage_bps=50) == 0.0


def test_bias_from_basis_positive_outside_costs():
    """20pp net basis → full MAX_BASIS_BIAS."""
    bias = bias_from_basis(0.25, fees_bps=500, slippage_bps=0)
    # net = 0.25 - 0.05 = 0.20 → full bias
    assert bias == pytest.approx(MAX_BASIS_BIAS, abs=1e-9)


def test_bias_from_basis_negative_sign_preserved():
    bias = bias_from_basis(-0.25, fees_bps=500, slippage_bps=0)
    assert bias == pytest.approx(-MAX_BASIS_BIAS, abs=1e-9)


def test_bias_from_basis_capped_at_max():
    """A 80pp spread doesn't bet 80pp — caps at MAX_BASIS_BIAS."""
    bias = bias_from_basis(0.80, fees_bps=500, slippage_bps=0)
    assert bias == pytest.approx(MAX_BASIS_BIAS, abs=1e-9)


def test_compose_basis_no_venue_returns_zero_bias():
    f = basis_compose(polymarket_p=0.50, venue_p=None)
    assert f.bias == 0.0
    assert f.tradable is False
    assert f.raw_spread is None


def test_compose_basis_tradable_when_costs_covered():
    f = basis_compose(polymarket_p=0.40, venue_p=0.60, fees_bps=500, slippage_bps=50)
    # spread 0.20, costs 0.055, net 0.145 > 0
    assert f.tradable is True
    assert f.bias > 0


def test_compose_basis_not_tradable_inside_costs():
    f = basis_compose(polymarket_p=0.50, venue_p=0.53, fees_bps=500, slippage_bps=50)
    # spread 0.03 < 0.055 cost
    assert f.tradable is False
    assert f.bias == 0.0


# ─── Perps signal ─────────────────────────────────────────────────────


def test_cascade_risk_neutral_when_no_data():
    """No funding + no OI → 0.5 baseline (no signal either way)."""
    assert cascade_risk(None, None) == 0.5


def test_cascade_risk_high_when_funding_extreme_positive():
    """+3σ funding + 20% OI growth → near 1.0."""
    r = cascade_risk(funding_z=3.0, oi_delta_pct=0.20)
    assert r > 0.85


def test_cascade_risk_low_when_funding_extreme_negative():
    """-3σ funding + flat OI → low risk."""
    r = cascade_risk(funding_z=-3.0, oi_delta_pct=0.0)
    assert r < 0.30


def test_perps_compose_no_bias_below_threshold():
    """|funding_z| < 1 → zero bias."""
    f = perps_compose(symbol="BTCUSDT", funding_z=0.5)
    assert f.directional_bias == 0.0


def test_perps_compose_contrarian_on_extreme_long_funding():
    """+3σ funding on yes_means_up market → negative bias (contrarian)."""
    f = perps_compose(symbol="BTCUSDT", funding_z=3.0)
    assert f.directional_bias < 0
    assert abs(f.directional_bias) <= MAX_PERPS_BIAS


def test_perps_compose_contrarian_on_extreme_short_funding():
    """-3σ funding on yes_means_up market → positive bias."""
    f = perps_compose(symbol="BTCUSDT", funding_z=-3.0)
    assert f.directional_bias > 0
    assert f.directional_bias <= MAX_PERPS_BIAS


def test_perps_compose_capped_at_max():
    f = perps_compose(symbol="BTCUSDT", funding_z=10.0)
    assert abs(f.directional_bias) <= MAX_PERPS_BIAS + 1e-9


# ─── CFTC positioning ────────────────────────────────────────────────


def test_cot_compose_no_data_no_bias():
    f = cot_compose(market_code="BTC", speculator_z=None)
    assert f.directional_bias == 0.0


def test_cot_compose_no_bias_below_threshold():
    f = cot_compose(market_code="BTC", speculator_z=0.5)
    assert f.directional_bias == 0.0


def test_cot_compose_crowded_longs_negative_bias():
    """+3σ crowded longs → contrarian negative bias (UP market)."""
    f = cot_compose(market_code="BTC", speculator_z=3.0)
    assert f.directional_bias < 0
    assert abs(f.directional_bias) <= MAX_COT_BIAS


def test_cot_compose_crowded_shorts_positive_bias():
    f = cot_compose(market_code="BTC", speculator_z=-3.0)
    assert f.directional_bias > 0


# ─── Scorer integration ──────────────────────────────────────────────


def _base(**overrides) -> MarketSnapshot:
    defaults = dict(
        market_id="0xtest",
        question="Will event X happen?",
        category="crypto",
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


def test_scorer_basis_arb_pulls_oracle_toward_venue():
    """Polymarket 0.40, venue 0.60 → tradable basis → YES bias."""
    sig = score_market(_base(
        basis_venue_implied=0.60,
        basis_venue_label="kalshi",
        basis_fees_bps=400.0,
        basis_slippage_bps=20.0,
    ))
    assert sig.oracle_probability > 0.50


def test_scorer_perps_extreme_funding_biases_no():
    """+3σ funding on a crypto UP-market → contrarian, oracle < market."""
    sig = score_market(_base(perps_funding_z=3.0))
    assert sig.oracle_probability < 0.50


def test_scorer_cot_crowded_longs_bias_no():
    sig = score_market(_base(cot_speculator_z=3.0))
    assert sig.oracle_probability < 0.50


def test_scorer_legacy_callers_unaffected_by_new_fields():
    """A snapshot without basis/perps/cot fields → identical signal
    to one with all three explicitly set to None."""
    a = score_market(_base())
    b = score_market(_base(
        basis_venue_implied=None,
        perps_funding_z=None,
        cot_speculator_z=None,
    ))
    assert a.oracle_probability == b.oracle_probability
    assert a.band_score == b.band_score


def test_scorer_all_seven_new_features_cap_oracle_movement():
    """All 7 new features pushing YES at once → oracle still inside
    [0, 1] and not wildly off. Per-feature caps × 7 = ±0.35 max."""
    sig = score_market(_base(
        gdelt_article_count=1000,
        gdelt_average_tone=-20.0,
        wikipedia_pageview_series=[100 + (i % 10) * 5 for i in range(27)] + [10_000] * 3,
        fred_latest_value=100.0,
        fred_threshold=0.0,
        fred_scale=0.1,
        manifold_implied=0.99,
        basis_venue_implied=0.99,
        perps_funding_z=-3.0,  # crowded shorts → YES bias
        cot_speculator_z=-3.0,  # crowded shorts → YES bias
    ))
    assert 0.0 < sig.oracle_probability < 1.0
    # All 7 pushing YES → oracle should be well above 0.50 but capped.
    assert 0.60 < sig.oracle_probability < 0.90
