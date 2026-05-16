"""Polymarket CLOB WebSocket L2 depth client.

The REST snapshot endpoint Apollo uses today gives best-bid + best-ask
only. For the order-book imbalance feature to actually have signal we
need *depth*, and depth changes faster than any polling cadence can
keep up with. Polymarket exposes a WebSocket at ``wss://ws-subscriptions-clob.polymarket.com/ws/market``
that streams L2 deltas: every book update is pushed in milliseconds.

This module maintains a synthetic L2 book per subscribed market and
emits a stream of ``OrderBookSnapshot`` events that Apollo's
``orderbook_imbalance`` feature can read directly via its native
``OrderBookLevel`` shape.

Failure model — Polymarket WS is the upstream truth; if it 4xx's or
drops, the client backs off + reconnects with exponential delay.
Apollo falls back to the REST snapshot when the WS stream is silent
longer than ``STALENESS_SECONDS``.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

import structlog

log = structlog.get_logger("pythia.polymarket_ws")

WS_URL = os.environ.get(
    "POLYMARKET_WS_URL",
    "wss://ws-subscriptions-clob.polymarket.com/ws/market",
)
RECONNECT_INITIAL_S = float(os.environ.get("POLYMARKET_WS_RECONNECT_INITIAL_S", "1.0"))
RECONNECT_MAX_S = float(os.environ.get("POLYMARKET_WS_RECONNECT_MAX_S", "60.0"))
STALENESS_SECONDS = int(os.environ.get("POLYMARKET_WS_STALENESS_S", "30"))


# Reuse Apollo's OrderBookLevel shape so the streamed book drops
# straight into orderbook_imbalance() without translation.
try:
    from apollo.features.orderbook_imbalance import OrderBookLevel  # type: ignore
except ImportError:
    # Apollo may not be importable from this service in some deploy
    # topologies; fall back to a local dataclass with the same shape.
    @dataclass(frozen=True)
    class OrderBookLevel:  # type: ignore[no-redef]
        price: float
        size_usdc: float


@dataclass
class OrderBookSnapshot:
    market_id: str
    bids: list[OrderBookLevel] = field(default_factory=list)
    asks: list[OrderBookLevel] = field(default_factory=list)
    seq: int = 0
    received_at: float = 0.0


class PolymarketL2Client:
    """One client per process. Subscribes to N markets, exposes a
    single async iterator of ``OrderBookSnapshot``.

    ``websockets`` is an optional dep — the client imports it lazily
    so unit tests can patch _open or feed snapshots directly through
    ``inject_for_testing``.
    """

    def __init__(self, market_ids: list[str]) -> None:
        self._market_ids = list(market_ids)
        self._queue: asyncio.Queue[OrderBookSnapshot] = asyncio.Queue(maxsize=1024)
        self._books: dict[str, OrderBookSnapshot] = {
            mid: OrderBookSnapshot(market_id=mid) for mid in self._market_ids
        }
        self._closed = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def close(self) -> None:
        self._closed = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def snapshots(self) -> AsyncIterator[OrderBookSnapshot]:
        """Async iterator the consumer (Apollo) drains."""
        while not self._closed:
            try:
                snap = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                yield snap
            except asyncio.TimeoutError:
                # Heartbeat — let the caller poll for staleness.
                continue

    def latest(self, market_id: str) -> Optional[OrderBookSnapshot]:
        """Synchronous accessor for the most-recent book by market."""
        return self._books.get(market_id)

    # ── Test seam — production path is _run() ─────────────────────

    def inject_for_testing(self, snapshot: OrderBookSnapshot) -> None:
        """Inject a snapshot as if it had arrived over the wire."""
        self._books[snapshot.market_id] = snapshot
        try:
            self._queue.put_nowait(snapshot)
        except asyncio.QueueFull:
            pass

    # ── Production WS loop ────────────────────────────────────────

    async def _run(self) -> None:
        backoff = RECONNECT_INITIAL_S
        while not self._closed:
            try:
                async with self._open() as ws:
                    backoff = RECONNECT_INITIAL_S
                    await self._subscribe(ws)
                    async for msg in ws:
                        await self._handle(msg)
            except asyncio.CancelledError:
                return
            except Exception as e:  # noqa: BLE001
                log.warning("polymarket_ws.disconnect", error=str(e), backoff=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_S)

    def _open(self):
        """Open the upstream WS. Separated so tests can patch it."""
        import websockets  # type: ignore

        return websockets.connect(WS_URL, ping_interval=20, ping_timeout=10)

    async def _subscribe(self, ws) -> None:
        # Polymarket expects {type: 'subscribe', channel: 'market', assets_ids: [...]}.
        # Schema has evolved over time so we keep the message shape minimal
        # and tolerant; operators tweak as needed when CLOB versions roll.
        await ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "channel": "market",
                    "assets_ids": self._market_ids,
                }
            )
        )

    async def _handle(self, raw: str) -> None:
        try:
            msg = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
        except (ValueError, TypeError):
            return
        if not isinstance(msg, dict):
            return
        market_id = msg.get("market") or msg.get("asset_id") or msg.get("market_id")
        if market_id is None or market_id not in self._books:
            return
        book = self._books[market_id]
        # Polymarket's L2 delta carries either a full snapshot or a
        # delta. We just rebuild the book from the supplied lists
        # whenever they are present — that handles both events cleanly.
        if "bids" in msg or "asks" in msg:
            book.bids = _parse_levels(msg.get("bids") or [])
            book.asks = _parse_levels(msg.get("asks") or [])
        book.seq += 1
        import time as _t

        book.received_at = _t.time()
        try:
            self._queue.put_nowait(book)
        except asyncio.QueueFull:
            # Drop on overflow — Apollo only cares about the most-recent
            # snapshot anyway; ``latest()`` always returns the freshest.
            pass


def _parse_levels(raw: list) -> list[OrderBookLevel]:
    out: list[OrderBookLevel] = []
    for entry in raw:
        try:
            if isinstance(entry, dict):
                price = float(entry.get("price"))
                size = float(entry.get("size") or entry.get("amount") or 0.0)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                price = float(entry[0])
                size = float(entry[1])
            else:
                continue
        except (TypeError, ValueError):
            continue
        if size > 0 and 0.0 <= price <= 1.0:
            out.append(OrderBookLevel(price=price, size_usdc=size))
    return out
