"""Tests for the TradingView screener adapter."""

from __future__ import annotations

from pythia.tradingview import (
    PRESET_OVERBOUGHT,
    PRESET_OVERSOLD,
    PRESET_TREND_BREAKOUT,
    ScreenerRow,
    fetch_screener,
)


def _stub_fetcher(rows: list[dict]):
    def _run(spec: dict) -> list[dict]:
        return rows
    return _run


def test_fetch_normalises_canonical_columns():
    rows = [
        {"ticker": "AAPL", "name": "Apple", "close": 200.5, "change": 1.2, "RSI": 65.0, "volume": 50_000_000},
        {"ticker": "TSLA", "name": "Tesla", "close": 220.0, "change": -2.5, "RSI": 45.0, "volume": 60_000_000},
    ]
    out = fetch_screener({}, fetcher=_stub_fetcher(rows))
    assert len(out) == 2
    assert out[0].symbol == "AAPL"
    assert out[0].close == 200.5
    assert out[0].rsi == 65.0


def test_fetch_handles_missing_columns():
    rows = [{"ticker": "X"}]
    out = fetch_screener({}, fetcher=_stub_fetcher(rows))
    assert out[0].close == 0.0
    assert out[0].rsi is None
    assert out[0].volume == 0.0


def test_fetch_returns_empty_when_fetcher_raises():
    def _bad(spec):
        raise RuntimeError("upstream is down")

    out = fetch_screener({}, fetcher=_bad)
    assert out == []


def test_fetch_extra_carries_unknown_columns():
    rows = [{"ticker": "X", "close": 1.0, "EMA200": 2.0, "MACD": 0.5}]
    out = fetch_screener({}, fetcher=_stub_fetcher(rows))
    assert "EMA200" in out[0].extra
    assert "MACD" in out[0].extra


def test_presets_are_dicts_with_expected_shape():
    for preset in (PRESET_OVERSOLD, PRESET_OVERBOUGHT, PRESET_TREND_BREAKOUT):
        assert isinstance(preset, dict)
        assert "filter" in preset
        assert "columns" in preset
        assert "sort" in preset


def test_screener_row_is_immutable():
    row = ScreenerRow(symbol="X", name="x", close=1.0, change_pct=0.0, rsi=None, volume=0.0, extra={})
    try:
        row.symbol = "Y"  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("ScreenerRow should be frozen")
