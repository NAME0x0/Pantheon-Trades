"""Deribit options — implied-vol source for crypto binaries.

Deribit publishes options chains for BTC, ETH, and a few others. The
public REST endpoints require no key and have generous rate limits.

For Polymarket / Kalshi binaries that resolve on a crypto price level
(``Will BTC be above $X by Y?``), the listed options at the nearest
expiry imply a forward probability distribution we can read directly.

Two endpoints we use:

  * ``/public/get_instruments`` — list active options for a currency.
  * ``/public/get_book_summary_by_instrument`` — per-instrument mark
    price + implied vol (mark_iv) + greeks.

Output for an Apollo feature:

  * ``atm_iv(currency, expiry_ms)`` — at-the-money implied vol for
    the nearest expiry on or after ``expiry_ms``.
  * ``implied_probability(currency, strike, expiry_ms)`` — uses the
    BS lognormal approximation P(S_T > K) = N(d2) with mark IV.

References:
  Deribit Pro API: https://docs.deribit.com/
  Black-Scholes d2 formula used for the lognormal probability.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pantheon_core.schema import utc_now

from pythia.base import DataSource, SourceSnapshot

API_BASE = "https://www.deribit.com/api/v2"

Currency = Literal["BTC", "ETH", "SOL"]


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via erf — no scipy dependency."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def lognormal_above(
    spot: float,
    strike: float,
    iv_annual: float,
    days_to_expiry: float,
    risk_free: float = 0.0,
) -> float:
    """Black-Scholes-implied P(S_T > strike) under lognormal dynamics.

    Closed-form: P = N(d2) where
        d2 = (ln(S/K) + (r - σ²/2) * T) / (σ * √T)

    Returns 0.0 / 1.0 on degenerate inputs.
    """
    if days_to_expiry <= 0 or iv_annual <= 0:
        return 1.0 if spot > strike else 0.0
    if spot <= 0 or strike <= 0:
        return 0.5
    T = days_to_expiry / 365.0
    sigma = iv_annual
    d2 = (math.log(spot / strike) + (risk_free - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))
    return _norm_cdf(d2)


class DeribitSource(DataSource):
    """Read-only Deribit public REST client."""

    name = "deribit"
    max_staleness_seconds = 60

    DEFAULT_CURRENCY: Currency = "BTC"

    async def fetch(self) -> SourceSnapshot:
        """Smoke fetch: list of active BTC option instruments."""
        instruments = await self.list_options(self.DEFAULT_CURRENCY)
        return SourceSnapshot(
            source=self.name,
            fetched_at=utc_now(),
            data={
                "currency": self.DEFAULT_CURRENCY,
                "instruments": instruments[:20],  # cap for size
                "n_total": len(instruments),
            },
        )

    async def list_options(self, currency: Currency) -> list[dict[str, Any]]:
        """List active option instruments for ``currency``."""
        resp = await self._client.get(
            f"{API_BASE}/public/get_instruments",
            params={"currency": currency, "kind": "option", "expired": "false"},
            timeout=15.0,
        )
        resp.raise_for_status()
        body = resp.json()
        return list(body.get("result", []))

    async def book_summary(
        self, instrument_name: str,
    ) -> dict[str, Any] | None:
        """Per-instrument mark price + mark IV + greeks."""
        resp = await self._client.get(
            f"{API_BASE}/public/get_book_summary_by_instrument",
            params={"instrument_name": instrument_name},
            timeout=10.0,
        )
        resp.raise_for_status()
        body = resp.json()
        rows = body.get("result", [])
        if not rows:
            return None
        return rows[0]

    async def index_price(self, currency: Currency) -> float | None:
        """Current Deribit index price for ``currency``."""
        resp = await self._client.get(
            f"{API_BASE}/public/get_index_price",
            params={"index_name": f"{currency.lower()}_usd"},
            timeout=10.0,
        )
        resp.raise_for_status()
        body = resp.json()
        result = body.get("result", {})
        try:
            return float(result.get("index_price", 0.0))
        except (TypeError, ValueError):
            return None

    async def atm_iv(self, currency: Currency, *, target_expiry_ms: int) -> float | None:
        """At-the-money implied vol for the option expiry nearest
        ``target_expiry_ms``.

        We pull the spot index, find the closest call strike, fetch
        its book summary, and read ``mark_iv`` (Deribit returns it in
        percent — convert to decimal).
        """
        spot = await self.index_price(currency)
        if spot is None:
            return None
        instruments = await self.list_options(currency)
        # Filter calls only; nearest expiry to target.
        calls = [
            i for i in instruments
            if i.get("option_type") == "call"
            and i.get("expiration_timestamp")
        ]
        if not calls:
            return None
        # Find the expiry bucket nearest target.
        def _expiry_diff(inst):
            try:
                return abs(int(inst["expiration_timestamp"]) - target_expiry_ms)
            except (KeyError, TypeError, ValueError):
                return 10 ** 18
        calls.sort(key=_expiry_diff)
        nearest_expiry = calls[0]["expiration_timestamp"]
        # Among instruments at that expiry, find the strike closest to spot.
        same_expiry = [c for c in calls if c["expiration_timestamp"] == nearest_expiry]
        def _strike_diff(inst):
            try:
                return abs(float(inst["strike"]) - spot)
            except (KeyError, TypeError, ValueError):
                return 10 ** 18
        same_expiry.sort(key=_strike_diff)
        atm = same_expiry[0]
        summary = await self.book_summary(atm["instrument_name"])
        if summary is None:
            return None
        mark_iv = summary.get("mark_iv")
        if mark_iv is None:
            return None
        try:
            return float(mark_iv) / 100.0  # Deribit returns percent
        except (TypeError, ValueError):
            return None

    async def implied_probability(
        self,
        currency: Currency,
        *,
        strike: float,
        expiry_ms: int,
    ) -> float | None:
        """Lognormal P(spot > strike at expiry) using ATM mark IV.

        Cheap approximation — uses ATM vol instead of the per-strike
        smile, but fine for sizing-grade probability priors.
        """
        spot = await self.index_price(currency)
        iv = await self.atm_iv(currency, target_expiry_ms=expiry_ms)
        if spot is None or iv is None:
            return None
        days_to_expiry = max(0.0, (expiry_ms / 1000.0 - utc_now().timestamp()) / 86400.0)
        return lognormal_above(
            spot=spot, strike=strike,
            iv_annual=iv, days_to_expiry=days_to_expiry,
        )
