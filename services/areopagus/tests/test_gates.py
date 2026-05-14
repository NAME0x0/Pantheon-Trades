from __future__ import annotations

from datetime import datetime, timezone

from pantheon_core.schema import Signal

from areopagus.gates import (
    MAX_SPREAD,
    MAX_STALENESS,
    MIN_LIQUIDITY,
    check_signal_gates,
)


def _signal(**kwargs) -> Signal:
    defaults = dict(
        market_id="0xtest",
        question="Test market",
        category="crypto",
        market_probability=0.45,
        oracle_probability=0.58,
        edge=0.13,
        edge_abs=0.13,
        band="A",
        band_score=0.72,
        liquidity_score=0.75,
        volatility_score=0.50,
        catalyst_score=0.60,
        sentiment_score=0.55,
        correlation_score=0.50,
        trend_score=0.60,
        volume_24h=100_000,
        open_interest=200_000,
        bid=0.44,
        ask=0.46,
        spread=0.02,
        days_to_resolution=20.0,
        data_sources=["polymarket"],
        staleness_seconds=30,
        source_trust_score=0.90,
        pythia_snapshot_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Signal(**defaults)


def test_valid_signal_passes():
    result = check_signal_gates(_signal())
    assert result.passed


def test_staleness_gate():
    result = check_signal_gates(_signal(staleness_seconds=MAX_STALENESS + 1))
    assert not result.passed
    assert "STALENESS" in result.reason_code


def test_spread_gate():
    result = check_signal_gates(_signal(spread=MAX_SPREAD + 0.01))
    assert not result.passed
    assert "SPREAD" in result.reason_code


def test_low_edge_gate():
    result = check_signal_gates(_signal(edge=0.02, edge_abs=0.02))
    assert not result.passed
    assert result.reason_code == "EDGE"


def test_low_liquidity_gate():
    result = check_signal_gates(_signal(liquidity_score=MIN_LIQUIDITY - 0.01))
    assert not result.passed
    assert result.reason_code == "LIQUIDITY"


def test_days_too_close():
    result = check_signal_gates(_signal(days_to_resolution=1.0))
    assert not result.passed


def test_days_too_far():
    result = check_signal_gates(_signal(days_to_resolution=200.0))
    assert not result.passed
