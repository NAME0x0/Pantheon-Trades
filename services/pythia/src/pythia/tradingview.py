"""TradingView screener adapter.

Backed by the open-source ``tradingview-screener`` PyPI package (MIT,
https://github.com/shner-elmo/TradingView-Screener) which exposes
TradingView's screener API without an API key.

We keep tradingview-screener as a *lazy* import so the apollo /
pythia runtime does not pay its weight unless screener pulls are
actually requested. Tests stub the upstream by passing an injectable
``fetcher`` callable.

Common screener rows:
  - symbol, name, exchange, sector
  - close, change, change_abs
  - RSI, MACD, EMA20/50/200
  - volume, market_cap_basic

This module returns plain dataclasses normalised to the columns we
care about. Caller maps them into Apollo features.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

# Pre-built screener strategies — operators can pass their own filter
# spec, but these cover most common quant setups.
PRESET_OVERSOLD = {
    "filter": [
        {"left": "RSI", "operation": "less", "right": 30},
        {"left": "volume", "operation": "greater", "right": 1_000_000},
    ],
    "columns": ["name", "close", "change", "RSI", "volume"],
    "sort": {"sortBy": "RSI", "sortOrder": "asc"},
}

PRESET_OVERBOUGHT = {
    "filter": [
        {"left": "RSI", "operation": "greater", "right": 70},
        {"left": "volume", "operation": "greater", "right": 1_000_000},
    ],
    "columns": ["name", "close", "change", "RSI", "volume"],
    "sort": {"sortBy": "RSI", "sortOrder": "desc"},
}

PRESET_TREND_BREAKOUT = {
    "filter": [
        {"left": "close", "operation": "greater", "right": "EMA200"},
        {"left": "EMA20", "operation": "greater", "right": "EMA50"},
        {"left": "change", "operation": "greater", "right": 2.0},
    ],
    "columns": ["name", "close", "change", "EMA20", "EMA50", "EMA200"],
    "sort": {"sortBy": "change", "sortOrder": "desc"},
}


@dataclass(frozen=True)
class ScreenerRow:
    symbol: str
    name: str
    close: float
    change_pct: float
    rsi: float | None
    volume: float
    extra: dict[str, Any]


Fetcher = Callable[[dict], list[dict]]
"""Pluggable callable. Real impl wraps the tradingview-screener Query;
tests pass a fixture that returns canned rows."""


def fetch_screener(
    spec: dict,
    *,
    fetcher: Fetcher | None = None,
    market: str = "america",
    limit: int = 100,
) -> list[ScreenerRow]:
    """Run a screener spec and return normalised rows.

    ``spec`` follows the tradingview-screener shape (filter / columns /
    sort). When ``fetcher`` is None we lazy-import the upstream lib;
    tests inject a deterministic stub.
    """
    runner: Fetcher = fetcher or _default_fetcher(market=market, limit=limit)
    try:
        raw = runner(spec)
    except Exception:  # noqa: BLE001
        return []
    return [_normalise(row) for row in raw]


def _default_fetcher(*, market: str, limit: int) -> Fetcher:
    """Build a fetcher that calls into ``tradingview-screener`` lazily."""

    def _run(spec: dict) -> list[dict]:
        try:
            from tradingview_screener import Query  # type: ignore[import-not-found]
        except ImportError as e:
            raise RuntimeError(
                "tradingview-screener is not installed; "
                "`uv add tradingview-screener`"
            ) from e
        q = Query().set_markets(market)
        if spec.get("filter"):
            # Translate generic spec into Query.where() column expressions.
            from tradingview_screener.column import Column  # type: ignore[import-not-found]

            exprs = []
            for f in spec["filter"]:
                col = Column(f["left"])
                op = f["operation"]
                right = f["right"]
                if op == "greater":
                    exprs.append(col > right)
                elif op == "less":
                    exprs.append(col < right)
                elif op == "equal":
                    exprs.append(col == right)
                elif op == "greater_or_equal":
                    exprs.append(col >= right)
                elif op == "less_or_equal":
                    exprs.append(col <= right)
            if exprs:
                q = q.where(*exprs)
        if spec.get("columns"):
            q = q.select(*spec["columns"])
        if spec.get("sort"):
            s = spec["sort"]
            q = q.order_by(s["sortBy"], ascending=(s.get("sortOrder", "asc") == "asc"))
        q = q.limit(limit)
        _, df = q.get_scanner_data()
        return df.to_dict(orient="records") if hasattr(df, "to_dict") else list(df)

    return _run


def _normalise(row: dict[str, Any]) -> ScreenerRow:
    return ScreenerRow(
        symbol=str(row.get("ticker") or row.get("symbol") or ""),
        name=str(row.get("name") or row.get("description") or ""),
        close=_safe_float(row.get("close")),
        change_pct=_safe_float(row.get("change")),
        rsi=_maybe_float(row.get("RSI") or row.get("rsi")),
        volume=_safe_float(row.get("volume")),
        extra={k: v for k, v in row.items() if k not in {"ticker", "symbol", "name", "description", "close", "change", "RSI", "rsi", "volume"}},
    )


def _safe_float(v: Any) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _maybe_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
