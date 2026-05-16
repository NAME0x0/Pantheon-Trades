"""Bloomberg-Terminal-replacement adapter.

OpenBB Terminal is the most mature open-source Bloomberg alternative
(MIT-licensed Python SDK that unifies 50+ data sources). The full SDK
is ~200 MB of dependencies which is too heavy to vendor here; instead
this module hits the same upstream endpoints OpenBB hits, but via
thin direct REST calls.

What this module covers, prioritised by what Pantheon actually needs:

  - **Equity OHLC** via Stooq (free, no key)
  - **FRED macro series** (US Federal Reserve Economic Data)
    via the public ``fred.stlouisfed.org/graph/fredgraph.csv`` endpoint
    that does not require an API key
  - **Crypto historical** via the existing CoinGecko adapter — already
    integrated in ``pythia/coingecko.py``

Heavier sources (Polygon, Finnhub, AlphaVantage, Quandl) require
API keys and are deliberately out of scope; document them in the
README so operators can wire them in via the same pattern when they
have keys.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
import structlog

log = structlog.get_logger("pythia.openbb_adapter")

STOOQ_URL = "https://stooq.com/q/d/l/"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
TIMEOUT_SECONDS = float(os.environ.get("OPENBB_TIMEOUT_S", "15"))


@dataclass(frozen=True)
class OHLCBar:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MacroPoint:
    date: datetime
    value: float


# ─── Equities via Stooq ──────────────────────────────────────────────


async def fetch_equity_ohlc(
    ticker: str,
    *,
    interval: str = "d",  # d=daily, w=weekly, m=monthly
) -> list[OHLCBar]:
    """Return Stooq OHLC bars for ``ticker``.

    Stooq uses lowercase tickers with a market suffix:
      - US equities: ``aapl.us``, ``msft.us``
      - ETFs: ``spy.us``
      - Indices: ``^spx``, ``^ndx``
    The function accepts both with-suffix and bare US tickers; we
    auto-append ``.us`` when no suffix is provided.
    """
    t = ticker.lower().strip()
    if "." not in t and not t.startswith("^"):
        t = f"{t}.us"
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as http:
        try:
            r = await http.get(STOOQ_URL, params={"s": t, "i": interval})
            if r.status_code != 200 or not r.text or r.text.startswith("<"):
                log.warning("pythia.openbb.stooq_empty", ticker=t)
                return []
        except Exception as e:  # noqa: BLE001
            log.warning("pythia.openbb.stooq_failed", error=str(e))
            return []

    return _parse_stooq_csv(r.text)


def _parse_stooq_csv(text: str) -> list[OHLCBar]:
    bars: list[OHLCBar] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        try:
            d = datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            bars.append(
                OHLCBar(
                    date=d,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume") or 0.0),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    return bars


# ─── FRED macro series ──────────────────────────────────────────────


async def fetch_fred_series(series_id: str) -> list[MacroPoint]:
    """Pull a macro time series from FRED.

    Series IDs are FRED's identifiers, e.g.:
      - ``DGS10``   10-year US treasury yield
      - ``DFF``     federal funds rate
      - ``CPIAUCSL`` consumer price index
      - ``VIXCLS``  CBOE VIX

    The graph endpoint returns CSV with two columns: DATE + the series.
    No API key required.
    """
    sid = series_id.upper().strip()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as http:
        try:
            r = await http.get(FRED_CSV, params={"id": sid})
            if r.status_code != 200 or not r.text:
                return []
        except Exception as e:  # noqa: BLE001
            log.warning("pythia.openbb.fred_failed", series=sid, error=str(e))
            return []
    return _parse_fred_csv(r.text, sid)


def _parse_fred_csv(text: str, series_id: str) -> list[MacroPoint]:
    out: list[MacroPoint] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        date_raw = row.get("DATE") or row.get("observation_date") or ""
        # Series column has the SID name.
        val_raw = row.get(series_id) or row.get("VALUE") or ""
        if not date_raw or val_raw in ("", ".", None):
            continue
        try:
            d = datetime.strptime(date_raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            v = float(val_raw)
        except (ValueError, TypeError):
            continue
        out.append(MacroPoint(date=d, value=v))
    return out


# ─── Optional yfinance bridge ───────────────────────────────────────


async def fetch_equity_yfinance(ticker: str, period: str = "1mo") -> list[OHLCBar]:
    """Pull OHLC via ``yfinance`` if installed; empty list otherwise.

    yfinance is a heavier dep (~5MB plus pandas). We keep it strictly
    optional — operators who want it pip-install separately. This
    function calls it in a thread so it doesn't block the event loop.
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        log.info("pythia.openbb.yfinance_not_installed")
        return []

    import asyncio
    import pandas as pd  # type: ignore

    def _sync_pull() -> list[OHLCBar]:
        try:
            df: pd.DataFrame = yf.Ticker(ticker).history(period=period)
        except Exception as e:  # noqa: BLE001
            log.warning("pythia.openbb.yfinance_failed", ticker=ticker, error=str(e))
            return []
        bars: list[OHLCBar] = []
        for ts, row in df.iterrows():
            try:
                bars.append(
                    OHLCBar(
                        date=ts.to_pydatetime().replace(tzinfo=timezone.utc),
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row.get("Volume") or 0.0),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return bars

    return await asyncio.to_thread(_sync_pull)
