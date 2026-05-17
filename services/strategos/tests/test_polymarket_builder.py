"""Tests for Polymarket V2 builder-code accounting.

Stays hermetic — no Polymarket calls. We exercise the math, the
config validation, and the projection helpers.
"""

from __future__ import annotations

import pytest

from strategos.polymarket_builder import (
    DEFAULT_BUILDER_SHARE,
    BuilderConfig,
    BuilderLedger,
    build_default_config,
    estimate_builder_fee_bps,
    project_revenue,
)


VALID_ADDR = "0x" + "ab" * 20


def test_builder_config_rejects_invalid_code():
    with pytest.raises(ValueError):
        BuilderConfig(code="", payout_address=VALID_ADDR)
    with pytest.raises(ValueError):
        BuilderConfig(code="x" * 33, payout_address=VALID_ADDR)


def test_builder_config_rejects_invalid_address():
    with pytest.raises(ValueError):
        BuilderConfig(code="pantheon", payout_address="not-an-address")
    with pytest.raises(ValueError):
        BuilderConfig(code="pantheon", payout_address="0xdead")


def test_builder_config_rejects_invalid_share():
    with pytest.raises(ValueError):
        BuilderConfig(code="pantheon", payout_address=VALID_ADDR, builder_share=-0.1)
    with pytest.raises(ValueError):
        BuilderConfig(code="pantheon", payout_address=VALID_ADDR, builder_share=1.5)


def test_builder_ledger_books_expected_fee():
    cfg = BuilderConfig(code="pantheon", payout_address=VALID_ADDR, builder_share=0.20)
    ledger = BuilderLedger(config=cfg)
    row = ledger.book(
        trade_id="t1",
        market_id="m1",
        category="politics",
        notional_usdc=1000.0,
    )
    # politics = 400 bps × $1000 × 0.20 = $8.00
    assert row.expected_builder_fee_usdc == pytest.approx(8.0)
    assert row.nominal_taker_fee_bps == 400.0
    assert row.builder_share == 0.20


def test_builder_ledger_geopolitics_zero_revenue():
    """V2 sets geopolitics fee=0 → builder fee=0."""
    cfg = BuilderConfig(code="pantheon", payout_address=VALID_ADDR)
    ledger = BuilderLedger(config=cfg)
    row = ledger.book(
        trade_id="t1",
        market_id="m1",
        category="geopolitics",
        notional_usdc=10_000.0,
    )
    assert row.expected_builder_fee_usdc == 0.0


def test_builder_ledger_totals_aggregate():
    cfg = BuilderConfig(code="pantheon", payout_address=VALID_ADDR, builder_share=0.25)
    ledger = BuilderLedger(config=cfg)
    ledger.book(trade_id="t1", market_id="m", category="crypto", notional_usdc=1000.0)
    ledger.book(trade_id="t2", market_id="m", category="politics", notional_usdc=500.0)
    tot = ledger.totals()
    # crypto: 720 × $1000 × 0.25 / 10000 = $18.00
    # politics: 400 × $500 × 0.25 / 10000 = $5.00
    assert tot["expected_builder_revenue_usdc"] == pytest.approx(23.0)
    assert tot["fills"] == 2.0
    assert tot["payout_address"] == VALID_ADDR
    assert tot["builder_code"] == "pantheon"


def test_builder_ledger_by_category_segments():
    cfg = BuilderConfig(code="pantheon", payout_address=VALID_ADDR)
    ledger = BuilderLedger(config=cfg)
    ledger.book(trade_id="t1", market_id="m", category="crypto", notional_usdc=1000.0)
    ledger.book(trade_id="t2", market_id="m", category="crypto", notional_usdc=2000.0)
    ledger.book(trade_id="t3", market_id="m", category="politics", notional_usdc=500.0)
    by_cat = ledger.by_category()
    assert by_cat["crypto"]["fills"] == 2.0
    assert by_cat["crypto"]["notional_usdc"] == pytest.approx(3000.0)
    assert by_cat["politics"]["fills"] == 1.0


def test_estimate_builder_fee_bps_by_category():
    """Builder fee bps = nominal taker bps × builder_share."""
    # politics = 400 bps × 0.20 = 80 bps
    assert estimate_builder_fee_bps("politics", builder_share=0.20) == pytest.approx(80.0)
    # crypto = 720 bps × 0.25 = 180 bps
    assert estimate_builder_fee_bps("crypto", builder_share=0.25) == pytest.approx(180.0)
    # geopolitics = 0 × anything = 0
    assert estimate_builder_fee_bps("geopolitics", builder_share=0.50) == 0.0


def test_estimate_builder_fee_bps_unknown_category_fallback():
    """Unknown category routes to 'other' (500 bps)."""
    assert estimate_builder_fee_bps("nonexistent", builder_share=0.10) == pytest.approx(50.0)


def test_project_revenue_returns_positive_annual_estimate():
    """10 fills/day × $1000 avg × politics-biased mix → real revenue."""
    p = project_revenue(
        n_fills_per_day=10,
        avg_notional_usdc=1000.0,
        category_mix={"politics": 1.0},
        builder_share=0.20,
    )
    # 10 × $1000 × 365 = $3.65M annual notional
    # politics 400 bps × 0.20 = 80 bps → $29,200 revenue
    assert p["annual_revenue_usdc"] == pytest.approx(29_200.0, abs=10)
    assert p["weighted_builder_bps"] == pytest.approx(80.0)


def test_project_revenue_default_mix():
    """Default mix is 50% politics / 30% sports / 20% economics."""
    p = project_revenue(n_fills_per_day=5, avg_notional_usdc=500.0)
    # weighted bps = 0.5×400 + 0.3×300 + 0.2×500 = 200 + 90 + 100 = 390
    # × DEFAULT_BUILDER_SHARE (0.20) = 78 bps
    assert p["weighted_builder_bps"] == pytest.approx(78.0)
    assert p["builder_share"] == DEFAULT_BUILDER_SHARE


def test_build_default_config_returns_none_when_env_missing(monkeypatch):
    monkeypatch.delenv("POLYMARKET_BUILDER_CODE", raising=False)
    monkeypatch.delenv("POLYMARKET_BUILDER_PAYOUT", raising=False)
    assert build_default_config() is None


def test_build_default_config_returns_config_when_set(monkeypatch):
    monkeypatch.setenv("POLYMARKET_BUILDER_CODE", "pantheon")
    monkeypatch.setenv("POLYMARKET_BUILDER_PAYOUT", VALID_ADDR)
    cfg = build_default_config()
    assert cfg is not None
    assert cfg.code == "pantheon"
    assert cfg.payout_address == VALID_ADDR


def test_build_default_config_returns_none_on_invalid(monkeypatch):
    monkeypatch.setenv("POLYMARKET_BUILDER_CODE", "pantheon")
    monkeypatch.setenv("POLYMARKET_BUILDER_PAYOUT", "not-valid")
    assert build_default_config() is None


def test_ledger_negative_notional_clamped():
    cfg = BuilderConfig(code="x", payout_address=VALID_ADDR)
    ledger = BuilderLedger(config=cfg)
    row = ledger.book(trade_id="t", market_id="m", category="crypto",
                      notional_usdc=-500.0)
    assert row.notional_usdc == 0.0
    assert row.expected_builder_fee_usdc == 0.0


def test_ledger_unknown_category_falls_back():
    cfg = BuilderConfig(code="x", payout_address=VALID_ADDR)
    ledger = BuilderLedger(config=cfg)
    row = ledger.book(trade_id="t", market_id="m", category="unknown_dance",
                      notional_usdc=1000.0)
    # other = 500 bps × 0.20 = 10 bps → $10
    assert row.expected_builder_fee_usdc == pytest.approx(10.0)
