"""Binance perpetual-futures funding rate + open-interest source.

Binance USDⓂ-M Futures public REST is free, no key, generous rate
limit (~1200 req/min weight-based). Two endpoints we need:

  * ``/fapi/v1/premiumIndex`` — current funding rate per symbol.
  * ``/fapi/v1/openInterest`` — current open interest per symbol.

For Polymarket markets like "Will BTC trade above $X by Y", the perps
funding rate + OI tell us where speculator positioning is *right now*.
Extreme positive funding (>+2σ in a rolling window) means longs are
heavily paying shorts — a classic over-leveraged signal that often
precedes a liquidation cascade.

What this module produces:

  * ``funding_rate(symbol)`` — current 8h funding rate.
  * ``funding_z(symbol, window)`` — z-score of latest funding vs a
    rolling history (pulled from ``/fapi/v1/fundingRate``).
  * ``open_interest(symbol)`` — current OI in USD-quote terms.
  * ``oi_delta(symbol, window)`` — percent change vs N samples ago.

We do not place trades. We do not authenticate. This is read-only
sentiment / positioning data feeding Apollo's ``perps_signal`` feature.
"""

from __future__ import annotations

import statistics
from typing import Any

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

API_BASE = "https://fapi.binance.com/fapi/v1"


class BinancePerpsSource(DataSource):
    """Read-only Binance USDⓂ-M futures REST client."""

    name = "binance_perps"
    max_staleness_seconds = 60

    DEFAULT_SYMBOL = "BTCUSDT"

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: BTCUSDT funding + OI."""
        funding = await self.funding_rate(self.DEFAULT_SYMBOL)
        oi = await self.open_interest(self.DEFAULT_SYMBOL)
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={"symbol": self.DEFAULT_SYMBOL, "funding": funding, "open_interest": oi},
        )

    async def funding_rate(self, symbol: str) -> dict[str, Any]:
        """Current funding (8h cycle). Returns ``{symbol, last_funding_rate,
        mark_price, next_funding_time}``.
        """
        resp = await self._client.get(
            f"{API_BASE}/premiumIndex",
            params={"symbol": symbol},
            timeout=10.0,
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "symbol": body.get("symbol"),
            "last_funding_rate": float(body.get("lastFundingRate", 0.0)),
            "mark_price": float(body.get("markPrice", 0.0)),
            "next_funding_time_ms": int(body.get("nextFundingTime", 0)),
        }

    async def funding_history(
        self,
        symbol: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Recent funding-rate history (one entry per 8h cycle)."""
        resp = await self._client.get(
            f"{API_BASE}/fundingRate",
            params={"symbol": symbol, "limit": str(limit)},
            timeout=15.0,
        )
        resp.raise_for_status()
        rows = resp.json()
        out: list[dict[str, Any]] = []
        for r in rows:
            try:
                out.append({
                    "funding_time_ms": int(r.get("fundingTime", 0)),
                    "funding_rate": float(r.get("fundingRate", 0.0)),
                })
            except (TypeError, ValueError):
                continue
        return out

    async def funding_z(
        self,
        symbol: str,
        *,
        window: int = 30,
    ) -> float | None:
        """Z-score of latest funding vs the last ``window`` cycles."""
        hist = await self.funding_history(symbol, limit=window + 1)
        if len(hist) < 5:
            return None
        # Last entry is the most recent — split off.
        rates = [h["funding_rate"] for h in hist[:-1]]
        latest = hist[-1]["funding_rate"]
        mu = statistics.fmean(rates)
        sd = statistics.pstdev(rates)
        if sd <= 0:
            return None
        return (latest - mu) / sd

    async def open_interest(self, symbol: str) -> dict[str, Any]:
        """Current open interest in contracts."""
        resp = await self._client.get(
            f"{API_BASE}/openInterest",
            params={"symbol": symbol},
            timeout=10.0,
        )
        resp.raise_for_status()
        body = resp.json()
        return {
            "symbol": body.get("symbol"),
            "open_interest": float(body.get("openInterest", 0.0)),
            "time_ms": int(body.get("time", 0)),
        }
