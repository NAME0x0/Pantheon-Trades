"""Circle Gateway — unified USDC balance across chains.

Gateway gives an agent a single USDC balance that's transparently
spendable on any supported chain, with sub-500ms cross-chain transfers
([source](https://developers.circle.com/stablecoins/gateway-overview)).
For an agent that trades on Polymarket (Polygon) AND wants to settle
on Arc, this removes the bridging step entirely.

This module is a thin async client. Operator-facing surface:

  * ``unified_balance()`` — total USDC across all chains in one number.
  * ``per_chain_balance()`` — segmented view for audit.
  * ``transfer_intent(target_chain, amount)`` — produces a
    serialisable record an upstream submitter can fire as a Gateway
    cross-chain transfer.

The actual chain-side execution lives in Circle's SDK. We expose the
*intent* layer so the rest of Pantheon stays chain-agnostic and the
tests don't need a real Gateway endpoint.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class GatewayBalance:
    """Snapshot of the unified balance + per-chain breakdown."""

    total_usdc: float
    per_chain: dict[str, float]
    snapshot_at: str


@dataclass(frozen=True)
class GatewayTransferIntent:
    """Upstream submitter consumes this to fire the cross-chain transfer."""

    source_chains: list[str]
    target_chain: str
    amount_usdc: float
    reason: str
    issued_at: str


class GatewayClient:
    """Async client for Circle Gateway.

    Same stub-friendly constructor pattern as the other Circle clients.
    """

    DEFAULT_BALANCE_URL = "https://api.circle.com/v1/gateway/balance"
    DEFAULT_TRANSFER_URL = "https://api.circle.com/v1/gateway/transfer"

    def __init__(
        self,
        client: Any,
        *,
        api_key: str | None = None,
        balance_url: str | None = None,
        transfer_url: str | None = None,
    ) -> None:
        self._client = client
        self._api_key = api_key or os.environ.get("CIRCLE_API_KEY", "")
        self._balance_url = balance_url or os.environ.get(
            "GATEWAY_BALANCE_URL", self.DEFAULT_BALANCE_URL
        )
        self._transfer_url = transfer_url or os.environ.get(
            "GATEWAY_TRANSFER_URL", self.DEFAULT_TRANSFER_URL
        )

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    async def balance(self, address: str) -> GatewayBalance:
        """Pull the unified balance for ``address`` across supported chains.

        On any error (network, auth, parse), returns an empty balance
        with snapshot_at set — callers should check ``total_usdc`` and
        ``per_chain`` before acting.
        """
        try:
            resp = await self._client.get(
                self._balance_url,
                params={"address": address},
                headers=self._auth_headers,
                timeout=10.0,
            )
            resp.raise_for_status()
            body = resp.json()
            per_chain_raw = body.get("perChain", {}) or {}
            per_chain = {str(k): float(v) for k, v in per_chain_raw.items()}
            total = float(body.get("totalUSDC", sum(per_chain.values())))
            return GatewayBalance(
                total_usdc=total,
                per_chain=per_chain,
                snapshot_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            return GatewayBalance(
                total_usdc=0.0,
                per_chain={},
                snapshot_at=datetime.now(timezone.utc).isoformat(),
            )

    async def unified_balance(self, address: str) -> float:
        """Convenience: just the total. Used by the dashboard."""
        b = await self.balance(address)
        return b.total_usdc

    async def per_chain_balance(self, address: str) -> dict[str, float]:
        """Convenience: just the per-chain breakdown."""
        b = await self.balance(address)
        return b.per_chain

    def transfer_intent(
        self,
        *,
        balance: GatewayBalance,
        target_chain: str,
        amount_usdc: float,
        prefer_drain: bool = False,
    ) -> GatewayTransferIntent:
        """Decide which source chains to draw from for a target transfer.

        Strategy: drain chains with the *smallest* balance first
        (default — concentrates liquidity on the target). Set
        ``prefer_drain=True`` to instead drain the largest first.
        """
        sources = [
            (chain, bal)
            for chain, bal in balance.per_chain.items()
            if chain != target_chain and bal > 0
        ]
        sources.sort(key=lambda x: x[1], reverse=prefer_drain)

        remaining = amount_usdc
        chosen: list[str] = []
        for chain, bal in sources:
            if remaining <= 0:
                break
            chosen.append(chain)
            remaining -= bal

        if remaining > 0:
            reason = (
                f"insufficient liquidity: need {amount_usdc:.2f}, "
                f"available {amount_usdc - remaining:.2f}"
            )
        else:
            reason = f"drain {len(chosen)} chain(s) into {target_chain}"
        return GatewayTransferIntent(
            source_chains=chosen,
            target_chain=target_chain,
            amount_usdc=amount_usdc,
            reason=reason,
            issued_at=datetime.now(timezone.utc).isoformat(),
        )


def balance_to_json(b: GatewayBalance) -> dict:
    return asdict(b)


def intent_to_json(intent: GatewayTransferIntent) -> dict:
    return asdict(intent)
