"""Polymarket CLOB client — thin async wrapper over py-clob-client.

``py_clob_client`` is synchronous and constructs signed orders against the
Polygon-side L2. We isolate its surface here so the rest of Strategos works
in async terms. Order signing requires the wallet private key passed at
construction; signing happens off-loop via ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

log = structlog.get_logger("strategos.clob")

DEFAULT_HOST = os.environ.get("POLYMARKET_CLOB", "https://clob.polymarket.com")
DEFAULT_CHAIN_ID = 137  # Polymarket settles on Polygon

Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class OrderRequest:
    token_id: str
    side: Side
    price: float
    size: float  # in contracts (not USDC)
    # CLOB v2 (April 2026) flags. `post_only=True` makes the exchange
    # reject our order rather than let it cross — required for maker-
    # rebate eligibility. Operator-supplied category routes to the
    # right fee bucket for ex-post rebate booking.
    post_only: bool = False
    category: str | None = None
    # Polymarket V2 builder code — see strategos.polymarket_builder.
    # When set, every fill on this order is attributed to our builder
    # program and pays a daily USDC fee to the registered payout
    # address. Independent of maker rebates.
    builder_code: str | None = None


@dataclass(frozen=True)
class OrderResponse:
    order_id: str
    status: str
    filled_size: float
    avg_price: float | None
    raw: dict[str, Any]


class PolymarketClobClient:
    """Wraps the synchronous py-clob-client with an async-safe surface."""

    def __init__(
        self,
        private_key: str | None = None,
        host: str = DEFAULT_HOST,
        chain_id: int = DEFAULT_CHAIN_ID,
    ) -> None:
        self._private_key = private_key or os.environ.get("PRIVATE_KEY")
        if not self._private_key:
            raise RuntimeError("PRIVATE_KEY env var required for Polymarket CLOB")
        self._host = host
        self._chain_id = chain_id
        self._client = None  # built lazily so unit tests can avoid the import

    def _ensure_client(self):
        if self._client is None:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import ApiCreds

            creds = ApiCreds(
                api_key=os.environ.get("POLYMARKET_API_KEY", ""),
                api_secret=os.environ.get("POLYMARKET_API_SECRET", ""),
                api_passphrase=os.environ.get("POLYMARKET_API_PASSPHRASE", ""),
            )
            self._client = ClobClient(
                host=self._host,
                key=self._private_key,
                chain_id=self._chain_id,
                creds=creds,
            )
        return self._client

    async def submit(self, order: OrderRequest) -> OrderResponse:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
        ):
            with attempt:
                return await asyncio.to_thread(self._submit_sync, order)
        raise RuntimeError("unreachable")

    def _submit_sync(self, order: OrderRequest) -> OrderResponse:
        from py_clob_client.clob_types import OrderArgs

        client = self._ensure_client()
        # OrderArgs in py-clob-client-v2 accepts `post_only`. Older v1
        # signatures (pre April 2026 EIP-712 v2 bump) ignored it; v2
        # respects it. We pass it unconditionally — operator on v1
        # silently gets a normal order, operator on v2 gets the flag.
        args_kwargs = {
            "price": order.price,
            "size": order.size,
            "side": order.side,
            "token_id": order.token_id,
        }
        if order.post_only:
            args_kwargs["post_only"] = True
        if order.builder_code:
            # py-clob-client-v2 accepts builder code as `builder_code`
            # (kebab on the wire, snake in the client). Some pre-v2
            # snapshots used `builderCode`; we pass the canonical one
            # and let the TypeError fallback below strip it if absent.
            args_kwargs["builder_code"] = order.builder_code
        try:
            args = OrderArgs(**args_kwargs)
        except TypeError:
            # v1 client doesn't know `post_only` / `builder_code`.
            # Strip both and retry — order still goes out, just without
            # the V2 attributions.
            args_kwargs.pop("post_only", None)
            args_kwargs.pop("builder_code", None)
            args = OrderArgs(**args_kwargs)
        signed = client.create_order(args)
        result = client.post_order(signed)
        log.info(
            "clob.order_submitted",
            token_id=order.token_id,
            side=order.side,
            price=order.price,
            size=order.size,
            order_id=result.get("orderID"),
        )
        return OrderResponse(
            order_id=str(result.get("orderID", "")),
            status=str(result.get("status", "unknown")),
            filled_size=float(result.get("filledSize", 0.0) or 0.0),
            avg_price=(
                float(result["averagePrice"]) if result.get("averagePrice") is not None else None
            ),
            raw=result,
        )

    async def cancel(self, order_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._cancel_sync, order_id)

    def _cancel_sync(self, order_id: str) -> dict[str, Any]:
        client = self._ensure_client()
        return client.cancel(order_id=order_id)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(lambda: self._ensure_client().get_order(order_id))

    async def get_book(self, token_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(lambda: self._ensure_client().get_order_book(token_id))
