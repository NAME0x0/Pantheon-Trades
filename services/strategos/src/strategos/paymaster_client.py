"""USDC-denominated gas via Circle Paymaster.

Circle's Paymaster lets users pay transaction fees in USDC instead of
the chain's native gas token. For an agent that holds USDC and never
ETH / MATIC / POL, this is the difference between "needs a separate
gas account top-up" and "spend the USDC you already have."

This module exposes a thin async client that:

  * Estimates a transaction's USDC gas cost given a wei-denominated
    gas estimate + a Paymaster-published USDC/wei rate.
  * Produces a ``GasIntent`` describing whether the transaction should
    be paid in native gas or routed through the Paymaster.

We do not embed actual paymaster signing logic — that lives in
Circle's SDK and depends on the chain + wallet kit version. This
module is the *accounting + routing* layer so an upstream submitter
knows which path to take.

Reference: https://developers.circle.com/stablecoins/paymaster-overview
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Literal

DEFAULT_USDC_PER_NATIVE = float(os.environ.get("PAYMASTER_USDC_PER_NATIVE", "0.003"))
DEFAULT_MARKUP_BPS = float(os.environ.get("PAYMASTER_MARKUP_BPS", "50"))  # 0.50%

GasMode = Literal["native", "paymaster_usdc"]


@dataclass(frozen=True)
class GasIntent:
    """The submitter consumes this to decide which gas path to use."""

    mode: GasMode
    estimated_native_wei: int
    estimated_usdc: float
    paymaster_markup_bps: float
    reason: str


@dataclass(frozen=True)
class PaymasterQuote:
    """Snapshot of the paymaster's USDC pricing."""

    usdc_per_native: float
    markup_bps: float

    def quote_usdc(self, native_wei: int) -> float:
        """Convert wei → USDC at the snapshot rate + markup."""
        native = native_wei / 1e18
        base = native * self.usdc_per_native
        return base * (1.0 + self.markup_bps / 10_000.0)


class PaymasterClient:
    """Async client for Circle's Paymaster.

    The constructor takes an httpx-like ``client`` (matches the
    DataSource pattern used elsewhere) so tests can swap a stub.
    The actual paymaster endpoint URL is operator-configurable —
    Circle publishes per-environment URLs and we read from env.
    """

    DEFAULT_QUOTE_URL = "https://api.circle.com/v1/paymaster/quote"

    def __init__(
        self,
        client: Any,
        *,
        quote_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._client = client
        self._quote_url = quote_url or os.environ.get(
            "PAYMASTER_QUOTE_URL", self.DEFAULT_QUOTE_URL
        )
        self._api_key = api_key or os.environ.get("CIRCLE_API_KEY", "")

    async def quote(self) -> PaymasterQuote:
        """Pull the current paymaster pricing.

        Falls back to the env-configured defaults on any error so the
        upstream submitter can still produce a sensible intent.
        """
        try:
            headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
            resp = await self._client.get(self._quote_url, headers=headers, timeout=10.0)
            resp.raise_for_status()
            body = resp.json()
            return PaymasterQuote(
                usdc_per_native=float(body.get("usdcPerNative", DEFAULT_USDC_PER_NATIVE)),
                markup_bps=float(body.get("markupBps", DEFAULT_MARKUP_BPS)),
            )
        except Exception:
            # Paymaster offline or refusing the request — return the
            # operator's expected rate so the submitter can decide
            # whether to proceed.
            return PaymasterQuote(
                usdc_per_native=DEFAULT_USDC_PER_NATIVE,
                markup_bps=DEFAULT_MARKUP_BPS,
            )

    async def decide(
        self,
        *,
        estimated_native_wei: int,
        native_balance_wei: int,
        usdc_balance: float,
        prefer_usdc: bool = True,
    ) -> GasIntent:
        """Decide native vs paymaster_usdc based on balances + prefs.

        Routing rules:
          1. If the wallet has insufficient native gas → must use paymaster.
          2. If operator prefers USDC AND wallet has enough USDC → paymaster.
          3. Otherwise → native (cheapest path).
        """
        q = await self.quote()
        usdc_cost = q.quote_usdc(estimated_native_wei)

        if native_balance_wei < estimated_native_wei:
            # No choice — paymaster.
            if usdc_balance < usdc_cost:
                # Both empty. Surface the intent anyway so the operator
                # sees what's needed.
                return GasIntent(
                    mode="paymaster_usdc",
                    estimated_native_wei=estimated_native_wei,
                    estimated_usdc=usdc_cost,
                    paymaster_markup_bps=q.markup_bps,
                    reason=f"insufficient native + USDC (need {usdc_cost:.6f}, have {usdc_balance:.6f})",
                )
            return GasIntent(
                mode="paymaster_usdc",
                estimated_native_wei=estimated_native_wei,
                estimated_usdc=usdc_cost,
                paymaster_markup_bps=q.markup_bps,
                reason="insufficient native gas, routing through Paymaster",
            )

        if prefer_usdc and usdc_balance >= usdc_cost:
            return GasIntent(
                mode="paymaster_usdc",
                estimated_native_wei=estimated_native_wei,
                estimated_usdc=usdc_cost,
                paymaster_markup_bps=q.markup_bps,
                reason="operator prefers USDC-denominated gas",
            )

        return GasIntent(
            mode="native",
            estimated_native_wei=estimated_native_wei,
            estimated_usdc=usdc_cost,
            paymaster_markup_bps=q.markup_bps,
            reason="native balance sufficient and cheaper",
        )


def intent_to_json(intent: GasIntent) -> dict:
    return asdict(intent)
