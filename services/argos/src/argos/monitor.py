"""Argos monitor — periodic loop that watches open positions and emits exits.

Each tick:
  1. Pull all open positions from the supplied source.
  2. Refresh each position's current side price by querying the price oracle.
  3. Apply ``check_exit`` to every position.
  4. Publish any resulting ExitSignals to Redis for Strategos to consume.

Failure isolation is per-position: an oracle error on one market never
prevents the rest of the book from being evaluated.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import structlog
from redis.asyncio import Redis

from pantheon_core.schema import ExitSignal

from argos.exits import check_exit
from argos.pnl import Position

log = structlog.get_logger("argos.monitor")

EXIT_STREAM = "argos:exits"
DEFAULT_INTERVAL = 15.0

PositionFetcher = Callable[[], Awaitable[list[Position]]]
PriceFetcher = Callable[[str], Awaitable[float | None]]


class ArgosMonitor:
    def __init__(
        self,
        get_positions: PositionFetcher,
        get_yes_price: PriceFetcher,
        redis: Redis,
        stream: str = EXIT_STREAM,
        interval_seconds: float = DEFAULT_INTERVAL,
    ) -> None:
        self._get_positions = get_positions
        self._get_yes_price = get_yes_price
        self._redis = redis
        self._stream = stream
        self._interval = interval_seconds

    async def tick(self) -> list[ExitSignal]:
        positions = await self._get_positions()
        exits: list[ExitSignal] = []
        for pos in positions:
            try:
                yes_price = await self._get_yes_price(pos.market_id)
            except Exception as e:
                log.warning(
                    "argos.price_fetch_failed",
                    market=pos.market_id,
                    error=str(e),
                )
                continue
            if yes_price is None:
                continue
            pos.update(yes_price)
            exit_signal = check_exit(pos)
            if exit_signal is not None:
                exits.append(exit_signal)
                await self._publish(exit_signal)
        log.info(
            "argos.tick",
            positions=len(positions),
            exits=len(exits),
        )
        return exits

    async def _publish(self, sig: ExitSignal) -> None:
        try:
            await self._redis.xadd(
                self._stream,
                {"data": sig.model_dump_json()},
                maxlen=50_000,
                approximate=True,
            )
        except Exception as e:
            log.warning("argos.publish_failed", trade_id=sig.trade_id, error=str(e))

    async def run_forever(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as e:
                log.exception("argos.tick_failed", error=str(e))
            await asyncio.sleep(self._interval)
