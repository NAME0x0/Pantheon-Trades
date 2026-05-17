"""Kalshi venue connector.

Kalshi is a US-regulated event-contracts exchange with a public REST
API. We expose it as a Pythia ``DataSource`` so signals can come from
Kalshi events with the same shape as Polymarket markets.

API docs: https://trading-api.readme.io/reference

Auth is API key + secret (RSA signed requests for trading; read-only
market data is public). This module only does **read** — fetching
event lists, markets, and quoted prices. Order submission belongs in
strategos and is intentionally out of scope here.
"""

from __future__ import annotations

from typing import Any

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

# Public read-only endpoint (no auth required for these calls).
API_BASE = "https://trading-api.kalshi.com/trade-api/v2"


class KalshiSource(DataSource):
    """Read-only market data from Kalshi's public REST API."""

    name = "kalshi"
    max_staleness_seconds = 90

    async def fetch(self) -> SourceSnapshot:
        """Fetch a top-level snapshot of active events."""
        resp = await self._client.get(
            f"{API_BASE}/events",
            params={"status": "open", "limit": 200},
            timeout=10.0,
        )
        resp.raise_for_status()
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={"events": resp.json().get("events", [])},
        )

    async def fetch_markets_for_event(self, event_ticker: str) -> list[dict]:
        resp = await self._client.get(
            f"{API_BASE}/markets",
            params={"event_ticker": event_ticker, "status": "open", "limit": 200},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("markets", [])

    async def fetch_market(self, ticker: str) -> dict:
        resp = await self._client.get(
            f"{API_BASE}/markets/{ticker}",
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("market", {})

    async def fetch_orderbook(self, ticker: str) -> dict:
        resp = await self._client.get(
            f"{API_BASE}/markets/{ticker}/orderbook",
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("orderbook", {"yes": [], "no": []})

    async def fetch_mid_price(self, ticker: str) -> float:
        """Return mid in [0, 1] derived from the YES side of the book.

        Kalshi quotes in *cents* (0–100). We return a probability in
        the [0, 1] convention so the downstream pipeline does not need
        to know which venue produced the price.
        """
        market = await self.fetch_market(ticker)
        bid = float(market.get("yes_bid", 0) or 0)
        ask = float(market.get("yes_ask", 100) or 100)
        # Kalshi cents -> [0, 1]. Clamp to avoid degenerate ranges.
        mid_cents = (bid + ask) / 2.0
        return max(0.0, min(1.0, mid_cents / 100.0))


def map_to_pantheon_market(market: dict[str, Any]) -> dict[str, Any]:
    """Normalise a Kalshi market into the same shape Apollo / Boule
    expect from Polymarket — minimal mapping, callers fill the rest.
    """
    bid = float(market.get("yes_bid", 0) or 0)
    ask = float(market.get("yes_ask", 100) or 100)
    return {
        "venue": "kalshi",
        "market_id": str(market.get("ticker", "")),
        "question": str(market.get("title") or market.get("subtitle") or ""),
        "category": str(market.get("category", "other")),
        "yes_bid": bid / 100.0,
        "yes_ask": ask / 100.0,
        "yes_mid": ((bid + ask) / 2.0) / 100.0,
        "volume_24h": float(market.get("volume", 0) or 0),
        "open_interest": float(market.get("open_interest", 0) or 0),
        "close_time": market.get("close_time"),
        "status": market.get("status", "unknown"),
    }
