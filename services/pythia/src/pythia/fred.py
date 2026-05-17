"""FRED — Federal Reserve Economic Data source.

FRED hosts 816,000+ macro time series, free, REST API. Most read
endpoints accept an empty / public API key for low-volume use. We
follow that contract: pass ``FRED_API_KEY`` if you have one (raises
rate limits from 120 req/min to 10x that), otherwise hit the public
fallback.

Docs: https://fred.stlouisfed.org/docs/api/fred/

For prediction markets, FRED is the obvious-but-rarely-wired source
for:

  * Fed decision binaries (read FEDFUNDS + DFEDTAR + breakeven inflation)
  * CPI / NFP binaries (read CPIAUCSL + PAYEMS lagged releases)
  * GDP nowcasts (read GDP + ATL Fed GDPNow scrape)
  * Inflation expectations (T5YIE, T10YIE)

This module returns latest observations + a basic delta-vs-target
helper. Apollo features layer on top.
"""

from __future__ import annotations

import os
from typing import Any

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

API_BASE = "https://api.stlouisfed.org/fred"
PUBLIC_KEY = "abcdefghijklmnopqrstuvwxyz123456"  # FRED's public fallback (32-char)


class FredSource(DataSource):
    """Federal Reserve Economic Data REST client."""

    name = "fred"
    # 5 min — FRED releases are slow enough that hot-caching costs us
    # almost nothing.
    max_staleness_seconds = 300

    DEFAULT_SERIES = "FEDFUNDS"  # benign smoke fetch

    def __init__(self, client, api_key: str | None = None) -> None:
        super().__init__(client)
        self._api_key = (
            api_key
            or os.environ.get("FRED_API_KEY")
            or PUBLIC_KEY
        )

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: latest observation of FEDFUNDS."""
        obs = await self.latest(self.DEFAULT_SERIES)
        return SourceSnapshot(source=self.name, fetched_at=utc_now(), data=obs)

    async def series_observations(
        self,
        series_id: str,
        *,
        limit: int = 30,
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Most-recent ``limit`` observations of a FRED series.

        Returns the raw list of {date, value, realtime_start, ...}
        records in the order requested.
        """
        params = {
            "series_id": series_id,
            "api_key": self._api_key,
            "file_type": "json",
            "limit": str(limit),
            "sort_order": sort_order,
        }
        resp = await self._client.get(
            f"{API_BASE}/series/observations", params=params, timeout=15.0
        )
        resp.raise_for_status()
        body = resp.json()
        return list(body.get("observations", []))

    async def latest(self, series_id: str) -> dict[str, Any]:
        """Most recent observation. Returns ``{series_id, date, value, value_float}``.

        FRED encodes missing data as the string ``"."`` — we surface
        ``value_float=None`` in that case rather than raise.
        """
        obs = await self.series_observations(series_id, limit=1, sort_order="desc")
        if not obs:
            return {"series_id": series_id, "date": None, "value": None, "value_float": None}
        first = obs[0]
        raw = first.get("value")
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = None
        return {
            "series_id": series_id,
            "date": first.get("date"),
            "value": raw,
            "value_float": val,
        }

    async def delta_vs(self, series_id: str, target: float) -> dict[str, Any]:
        """How far is the latest print from a target value?

        Used by Apollo when the prediction market explicitly anchors
        on a value (e.g. "Fed Funds > 4.5%?" → compare latest FEDFUNDS
        to 4.5).
        """
        latest = await self.latest(series_id)
        v = latest.get("value_float")
        delta = (v - target) if v is not None else None
        return {
            **latest,
            "target": target,
            "delta": delta,
        }

    async def percent_change(
        self,
        series_id: str,
        *,
        lookback: int = 12,
    ) -> dict[str, Any]:
        """Latest YoY (or N-period) percent change. Used for inflation
        / growth markets where the binary is on the change, not level."""
        obs = await self.series_observations(series_id, limit=lookback + 1, sort_order="desc")
        if len(obs) < lookback + 1:
            return {"series_id": series_id, "pct_change": None, "from": None, "to": None}
        try:
            latest = float(obs[0]["value"])
            prior = float(obs[lookback]["value"])
        except (KeyError, TypeError, ValueError):
            return {"series_id": series_id, "pct_change": None, "from": None, "to": None}
        if prior == 0:
            return {"series_id": series_id, "pct_change": None, "from": obs[lookback].get("date"),
                    "to": obs[0].get("date")}
        return {
            "series_id": series_id,
            "from": obs[lookback].get("date"),
            "to": obs[0].get("date"),
            "pct_change": (latest - prior) / abs(prior),
        }
