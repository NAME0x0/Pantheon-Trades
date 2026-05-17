"""CFTC Commitments of Traders (CoT) source.

Every Tuesday the CFTC releases positioning of large commercial and
speculative traders in major US futures markets. The *commercial-net*
position against the *non-commercial-net* (speculator) position is a
well-documented mean-reversion signal at multi-month horizons.

For Polymarket / Kalshi markets that resolve on a futures-traded
underlying (oil, gold, wheat, S&P 500 index, treasuries), CoT
positioning is a textbook contrarian indicator.

API: https://publicreporting.cftc.gov/resource/6dca-aqww.json
(Socrata Open Data — free, no key required for low-volume use.)

This module fetches the latest report for a market and exposes:

  * ``latest_positioning(market_code)`` — most recent week's
    commercial / non-commercial / non-reportable net positions.
  * ``positioning_z(market_code, window)`` — z-score of the
    speculator-net position vs the last ``window`` weeks.
"""

from __future__ import annotations

import statistics
from typing import Any

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

# Socrata API for CFTC CoT — financial-futures variant works for most
# Polymarket-relevant markets. For ag commodities a different dataset
# id may be used; the operator can override.
API_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"


class CftcSource(DataSource):
    """CFTC Commitments of Traders REST source."""

    name = "cftc"
    # Weekly releases — 4h cache is plenty.
    max_staleness_seconds = 4 * 3600

    DEFAULT_MARKET = "BITCOIN - CHICAGO MERCANTILE EXCHANGE"

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: latest Bitcoin CME futures positioning."""
        out = await self.latest_positioning(self.DEFAULT_MARKET)
        return SourceSnapshot(source=self.name, fetched_at=utc_now(), data=out or {})

    async def recent_reports(
        self,
        market_code: str,
        *,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Pull the last ``limit`` weekly reports for ``market_code``.

        Filter is a SoQL ``market_and_exchange_names`` substring match
        — CFTC uses the human-readable contract name as the key.
        """
        params = {
            "$where": f"market_and_exchange_names like '%{market_code}%'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": str(limit),
        }
        resp = await self._client.get(API_BASE, params=params, timeout=20.0)
        resp.raise_for_status()
        return list(resp.json())

    async def latest_positioning(self, market_code: str) -> dict[str, Any] | None:
        """Most recent report. Returns the parsed positioning dict or
        ``None`` if nothing matches."""
        rows = await self.recent_reports(market_code, limit=1)
        if not rows:
            return None
        r = rows[0]
        try:
            comm_long = float(r.get("comm_positions_long_all", 0))
            comm_short = float(r.get("comm_positions_short_all", 0))
            non_comm_long = float(r.get("noncomm_positions_long_all", 0))
            non_comm_short = float(r.get("noncomm_positions_short_all", 0))
        except (TypeError, ValueError):
            return None
        return {
            "market": r.get("market_and_exchange_names"),
            "report_date": r.get("report_date_as_yyyy_mm_dd"),
            "commercial_net": comm_long - comm_short,
            "non_commercial_net": non_comm_long - non_comm_short,
            "open_interest": float(r.get("open_interest_all", 0)),
        }

    async def positioning_z(
        self,
        market_code: str,
        *,
        window: int = 26,
    ) -> float | None:
        """Z-score of the most recent speculator-net vs the rolling window.

        Extreme positive (>+2σ) = crowded long speculator positioning;
        contrarian signal that a top is forming. Negative = crowded short.
        """
        rows = await self.recent_reports(market_code, limit=window + 1)
        if len(rows) < 5:
            return None
        nets: list[float] = []
        for r in rows:
            try:
                long_ = float(r.get("noncomm_positions_long_all", 0))
                short_ = float(r.get("noncomm_positions_short_all", 0))
                nets.append(long_ - short_)
            except (TypeError, ValueError):
                continue
        if len(nets) < 5:
            return None
        latest = nets[0]
        history = nets[1:]
        mu = statistics.fmean(history)
        sd = statistics.pstdev(history)
        if sd <= 0:
            return None
        return (latest - mu) / sd
