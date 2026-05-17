"""Manifold Markets — free play-money prediction market.

Manifold has 30k+ binary markets, generous public API, CC-BY-SA data.
Useful as:

  * A real-time *human consensus* prior on the same questions
    Polymarket prices. The gap between Manifold consensus and
    Polymarket implied is a calibration signal — not direct alpha,
    but a useful cross-check before sizing.

  * A *backtest substrate*. Manifold has resolved markets with
    known outcomes that we can replay through the Boule council to
    measure Brier score against play-money-but-incentivised humans.

API docs: https://docs.manifold.markets/api
No key required for read-only endpoints.
"""

from __future__ import annotations

from typing import Any

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

API_BASE = "https://api.manifold.markets/v0"


class ManifoldSource(DataSource):
    """Read-only Manifold Markets REST client."""

    name = "manifold"
    max_staleness_seconds = 120

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: latest 10 active markets."""
        markets = await self.list_markets(limit=10)
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={"markets": markets},
        )

    async def list_markets(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """List recently-traded markets. Default 100, max 1000."""
        resp = await self._client.get(
            f"{API_BASE}/markets",
            params={"limit": str(min(1000, max(1, limit)))},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def get_market(self, market_id: str) -> dict[str, Any]:
        """Full market record by Manifold id."""
        resp = await self._client.get(
            f"{API_BASE}/market/{market_id}", timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()

    async def search_markets(
        self,
        query: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Free-text search. Returns ranked binary markets matching ``query``."""
        resp = await self._client.get(
            f"{API_BASE}/search-markets",
            params={"term": query, "limit": str(limit)},
            timeout=15.0,
        )
        resp.raise_for_status()
        body = resp.json()
        # The endpoint returns a list directly in modern versions.
        return body if isinstance(body, list) else body.get("markets", [])

    async def implied_probability(self, market_id: str) -> float | None:
        """Manifold's current implied probability for a BINARY market.

        Returns ``None`` if the market is not binary or has no
        probability set (e.g. non-binary market types).
        """
        m = await self.get_market(market_id)
        if m.get("outcomeType") != "BINARY":
            return None
        p = m.get("probability")
        try:
            return float(p) if p is not None else None
        except (TypeError, ValueError):
            return None

    async def resolved_binary_markets(
        self,
        *,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Pull resolved binary markets — used by the backtest harness.

        Filters the bulk markets endpoint for ``isResolved=True``,
        ``outcomeType=BINARY``, and returns the subset.
        """
        rows = await self.list_markets(limit=limit)
        return [
            m
            for m in rows
            if m.get("isResolved") and m.get("outcomeType") == "BINARY"
        ]

    async def consensus_delta(
        self,
        manifold_id: str,
        polymarket_implied: float,
    ) -> dict[str, Any]:
        """``manifold_p - polymarket_p`` for the same question.

        Positive means Manifold consensus is more YES than Polymarket;
        negative the inverse. The magnitude is a sizing input only —
        large gaps deserve more research, not bigger positions.
        """
        m_p = await self.implied_probability(manifold_id)
        if m_p is None:
            return {"manifold_p": None, "polymarket_p": polymarket_implied, "delta": None}
        return {
            "manifold_p": m_p,
            "polymarket_p": polymarket_implied,
            "delta": m_p - polymarket_implied,
        }
