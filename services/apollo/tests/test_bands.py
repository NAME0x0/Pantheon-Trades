from __future__ import annotations

from apollo.bands import classify, classify_band, compute_band_score, is_eligible_for_boule


def test_band_S_signal():
    # All features near max -> S band.
    composite = compute_band_score(
        edge_abs=0.30,
        liquidity_score=0.95,
        catalyst_score=0.95,
        sentiment_score=0.95,
        trend_score=0.95,
        correlation_score=0.95,
    )
    assert classify_band(0.30, 0.95, composite) == "S"


def test_band_A_signal():
    composite = compute_band_score(
        edge_abs=0.20,
        liquidity_score=0.90,
        catalyst_score=0.80,
        sentiment_score=0.70,
        trend_score=0.70,
        correlation_score=0.80,
    )
    assert classify_band(0.20, 0.90, composite) in ("S", "A")


def test_band_below_floor_returns_D():
    composite = compute_band_score(0.01, 0.10, 0.10, 0.10, 0.10, 0.10)
    assert classify_band(0.01, 0.10, composite) == "D"


def test_eligibility_only_S_and_A():
    assert is_eligible_for_boule("S")
    assert is_eligible_for_boule("A")
    for band in ("B", "C", "D"):
        assert not is_eligible_for_boule(band)


def test_classify_returns_eligibility_for_S():
    result = classify(0.20, 0.90, 0.80, 0.70, 0.70, 0.80)
    assert result.band in ("S", "A")
    assert result.eligible is True


def test_composite_clamps_negative_inputs():
    composite = compute_band_score(-0.05, -0.10, -1.0, -1.0, -1.0, -1.0)
    assert composite >= 0.0
