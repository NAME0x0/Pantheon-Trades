"""Tests for the conformal-Kelly sizing path."""

from __future__ import annotations

import pytest

from areopagus.kelly import (
    DEFAULT_MAX_PCT,
    size_position,
    size_position_conformal,
)


def test_conformal_kelly_at_zero_q_hat_matches_point_estimate():
    """q_hat=0 ⇒ conformal lower bound = point estimate ⇒ same size."""
    p_size, p_kelly, p_reason = size_position(
        directional_edge=0.10,
        entry_price=0.40,
    )
    c_size, c_kelly, c_reason, diag = size_position_conformal(
        council_p_point=0.50,
        market_p=0.40,
        direction="YES",
        q_hat=0.0,
    )
    assert c_size == pytest.approx(p_size)
    assert c_kelly == pytest.approx(p_kelly)
    assert c_reason == p_reason
    assert diag["edge_point"] == diag["edge_conservative"]


def test_conformal_kelly_widens_at_tail_extreme():
    """High q_hat shrinks the conservative p (toward 0.50) and thus
    shrinks the directional edge → smaller position size.

    Use a council probability + market gap such that neither size
    hits ``max_pct=0.05`` cap, otherwise both sizes collapse to the
    cap and the test compares cap-vs-cap. With council_p=0.60 and
    market_p=0.45, half-Kelly is ~12% raw (over cap), so we widen
    enough to force the conservative half-Kelly below the cap.
    """
    c_size_tight, _, _, _ = size_position_conformal(
        council_p_point=0.60, market_p=0.45, direction="YES", q_hat=0.02,
        max_pct=0.20,  # raise cap so the test sees the actual half-Kelly
    )
    c_size_wide, _, _, _ = size_position_conformal(
        council_p_point=0.60, market_p=0.45, direction="YES", q_hat=0.10,
        max_pct=0.20,
    )
    assert c_size_wide < c_size_tight


def test_conformal_kelly_no_trade_when_q_hat_eats_edge():
    """Conformal p_lo < market_p ⇒ no conservative edge ⇒ no_edge."""
    size, _, reason, diag = size_position_conformal(
        council_p_point=0.55, market_p=0.50, direction="YES", q_hat=0.30,
    )
    # p_lo = 0.55 - 0.30 = 0.25, market_p=0.50, edge_conservative = 0
    assert reason == "no_edge"
    assert size == 0.0
    assert diag["p_used_for_kelly"] == pytest.approx(0.25)


def test_conformal_kelly_no_direction():
    """For a NO trade, conservative p comes from p_hi side."""
    size, _, _, diag = size_position_conformal(
        council_p_point=0.30, market_p=0.50, direction="NO", q_hat=0.05,
    )
    # p_hi = 0.35; conservative NO-side p = 1 - 0.35 = 0.65
    # Market NO-side = 1 - 0.50 = 0.50. Edge = 0.15.
    assert diag["p_used_for_kelly"] == pytest.approx(0.65)
    assert diag["edge_conservative"] == pytest.approx(0.15)
    assert size > 0


def test_conformal_kelly_rejects_unknown_direction():
    with pytest.raises(ValueError):
        size_position_conformal(
            council_p_point=0.5, market_p=0.5, direction="MAYBE", q_hat=0.05,
        )


def test_conformal_kelly_clamps_at_max_pct():
    """Even with a huge conservative edge, sizing is bounded by max_pct."""
    size, _, reason, _ = size_position_conformal(
        council_p_point=0.99,
        market_p=0.10,
        direction="YES",
        q_hat=0.01,
        max_pct=DEFAULT_MAX_PCT,
    )
    assert reason == "capped"
    assert size == pytest.approx(DEFAULT_MAX_PCT)


def test_conformal_kelly_diagnostics_completeness():
    """Diagnostics dict must include every documented key."""
    _, _, _, diag = size_position_conformal(
        council_p_point=0.60, market_p=0.50, direction="YES", q_hat=0.05,
    )
    expected = {"p_lo", "p_hi", "p_point", "p_used_for_kelly",
                "edge_point", "edge_conservative", "q_hat", "alpha"}
    assert expected.issubset(diag.keys())


def test_conformal_kelly_p_used_clamped_at_unit():
    """Council probability at 0.99 + tiny q_hat shouldn't break clamping."""
    _, _, _, diag = size_position_conformal(
        council_p_point=0.99, market_p=0.50, direction="YES", q_hat=0.05,
    )
    assert 0.0 <= diag["p_lo"] <= 1.0
    assert 0.0 <= diag["p_hi"] <= 1.0


def test_conformal_kelly_is_always_less_or_equal_to_point():
    """For positive q_hat, conformal sizing must never exceed point sizing."""
    for council_p in (0.55, 0.60, 0.70, 0.80, 0.90):
        for market_p in (0.30, 0.40, 0.50, 0.60):
            point_size, _, _ = size_position(
                directional_edge=max(0.0, council_p - market_p),
                entry_price=market_p,
            )
            conf_size, _, _, _ = size_position_conformal(
                council_p_point=council_p, market_p=market_p,
                direction="YES", q_hat=0.05,
            )
            assert conf_size <= point_size + 1e-9
