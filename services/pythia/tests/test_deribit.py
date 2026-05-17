"""Hermetic tests for the Deribit options source.

Stubs the public REST client; verifies the Black-Scholes math, the
nearest-expiry / nearest-strike selection, and graceful degradation."""

from __future__ import annotations


import pytest

from pythia.deribit import (
    DeribitSource,
    _norm_cdf,
    lognormal_above,
)


class _StubResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _StubClient:
    def __init__(self, payloads_by_path):
        # Map: path-substring → payload (consumed once per call).
        self._payloads = {k: list(v) for k, v in payloads_by_path.items()}
        self.calls = []

    async def get(self, url, *, params=None, timeout=10.0):
        self.calls.append((url, params or {}))
        for key, queue in self._payloads.items():
            if key in url:
                if not queue:
                    return _StubResp(200, {})
                return _StubResp(200, queue.pop(0))
        return _StubResp(404, {})


# ─── Math ─────────────────────────────────────────────────────────────


def test_norm_cdf_canonical_values():
    """Standard normal CDF anchors."""
    assert _norm_cdf(0.0) == pytest.approx(0.5)
    assert _norm_cdf(1.0) == pytest.approx(0.8413, abs=0.001)
    assert _norm_cdf(-1.0) == pytest.approx(0.1587, abs=0.001)
    assert _norm_cdf(1.96) == pytest.approx(0.975, abs=0.001)


def test_lognormal_above_at_money_zero_time():
    """Spot == strike, T → 0 ⇒ probability collapses to 0 or 1 depending on direction."""
    # T=0: code returns 1.0 if spot > strike else 0.0.
    assert lognormal_above(100.0, 100.0, 0.5, 0.0) == 0.0
    assert lognormal_above(101.0, 100.0, 0.5, 0.0) == 1.0
    assert lognormal_above(99.0, 100.0, 0.5, 0.0) == 0.0


def test_lognormal_above_at_money_positive_time():
    """At-the-money, σ=0.5, T=1yr ⇒ P should be < 0.5 due to drag term."""
    p = lognormal_above(100.0, 100.0, 0.5, days_to_expiry=365)
    # d2 = (0 + (-0.125)) / (0.5) = -0.25 ⇒ N(-0.25) ≈ 0.401
    assert 0.35 < p < 0.45


def test_lognormal_above_deep_in_the_money():
    """Spot far above strike ⇒ probability near 1.0."""
    p = lognormal_above(200.0, 100.0, 0.5, days_to_expiry=30)
    assert p > 0.95


def test_lognormal_above_deep_out_of_money():
    p = lognormal_above(50.0, 100.0, 0.5, days_to_expiry=30)
    assert p < 0.05


def test_lognormal_above_zero_iv_returns_direction_only():
    """No volatility ⇒ deterministic outcome by spot vs strike."""
    assert lognormal_above(100, 99, iv_annual=0.0, days_to_expiry=30) == 1.0
    assert lognormal_above(100, 101, iv_annual=0.0, days_to_expiry=30) == 0.0


def test_lognormal_above_degenerate_inputs():
    """Zero spot or strike ⇒ 0.5 fallback."""
    assert lognormal_above(0, 100, 0.5, 30) == 0.5
    assert lognormal_above(100, 0, 0.5, 30) == 0.5


# ─── Client ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_options_returns_results():
    client = _StubClient({
        "get_instruments": [{"result": [
            {"instrument_name": "BTC-30JAN26-100000-C", "option_type": "call",
             "expiration_timestamp": 1738195200000, "strike": 100000},
        ]}],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    out = await src.list_options("BTC")
    assert len(out) == 1


@pytest.mark.asyncio
async def test_book_summary_parses_first_row():
    client = _StubClient({
        "get_book_summary_by_instrument": [{"result": [
            {"instrument_name": "BTC-30JAN26-100000-C", "mark_iv": 65.0, "mark_price": 0.05},
        ]}],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    out = await src.book_summary("BTC-30JAN26-100000-C")
    assert out is not None
    assert out["mark_iv"] == 65.0


@pytest.mark.asyncio
async def test_book_summary_returns_none_on_empty():
    client = _StubClient({
        "get_book_summary_by_instrument": [{"result": []}],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    assert await src.book_summary("X") is None


@pytest.mark.asyncio
async def test_index_price_parsed():
    client = _StubClient({
        "get_index_price": [{"result": {"index_price": 85000.0}}],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    p = await src.index_price("BTC")
    assert p == 85000.0


@pytest.mark.asyncio
async def test_atm_iv_finds_nearest_strike_and_expiry():
    """3 instruments, 2 expiries. Spot 100k, target expiry matches 1738.
    Closest expiry has strikes 95k, 100k, 110k — ATM should pick 100k.
    """
    client = _StubClient({
        "get_index_price": [{"result": {"index_price": 100000.0}}],
        "get_instruments": [{"result": [
            {"instrument_name": "BTC-A", "option_type": "call",
             "expiration_timestamp": 1738195200000, "strike": 95000},
            {"instrument_name": "BTC-B", "option_type": "call",
             "expiration_timestamp": 1738195200000, "strike": 100000},
            {"instrument_name": "BTC-C", "option_type": "call",
             "expiration_timestamp": 1738195200000, "strike": 110000},
            {"instrument_name": "BTC-D", "option_type": "call",
             "expiration_timestamp": 1900000000000, "strike": 100000},
        ]}],
        "get_book_summary_by_instrument": [
            {"result": [{"mark_iv": 60.0}]},  # BTC-B (closest strike at closest expiry)
        ],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    iv = await src.atm_iv("BTC", target_expiry_ms=1738195200000)
    # 60% returned as 0.60 (Deribit publishes percent)
    assert iv == pytest.approx(0.60)


@pytest.mark.asyncio
async def test_atm_iv_returns_none_when_no_options():
    client = _StubClient({
        "get_index_price": [{"result": {"index_price": 100000.0}}],
        "get_instruments": [{"result": []}],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    assert await src.atm_iv("BTC", target_expiry_ms=1738195200000) is None


@pytest.mark.asyncio
async def test_implied_probability_uses_lognormal():
    """Spot 100k, strike 100k, IV 60%, T=30d → mid-ish probability."""
    client = _StubClient({
        "get_index_price": [
            {"result": {"index_price": 100000.0}},
            {"result": {"index_price": 100000.0}},
        ],
        "get_instruments": [{"result": [
            {"instrument_name": "BTC-B", "option_type": "call",
             "expiration_timestamp": 1738195200000, "strike": 100000},
        ]}],
        "get_book_summary_by_instrument": [
            {"result": [{"mark_iv": 60.0}]},
        ],
    })
    src = DeribitSource(client=client)  # type: ignore[arg-type]
    # Use a future expiry well past now so days_to_expiry > 0.
    import time as _t
    future_ms = int((_t.time() + 86400 * 30) * 1000)
    p = await src.implied_probability(
        "BTC", strike=100000, expiry_ms=future_ms,
    )
    assert p is not None
    # ATM at 60% IV, 30 days ⇒ slightly under 0.50 due to lognormal drag.
    assert 0.40 < p < 0.55
