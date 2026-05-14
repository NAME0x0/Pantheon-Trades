"""Settlement watcher — polls Polymarket for resolved markets and books PnL.

Argos watches open positions for exits *during* a market's life. The
settlement watcher handles the terminal event: once a market resolves, we
mark all trades against it as settled, compute realised PnL, and emit an
``ostrakon`` score event so agent credibility weights can update.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import structlog

from pantheon_core.schema import Trade

log = structlog.get_logger("strategos.settlement")

ResolveFn = Callable[[str], Awaitable[float | None]]
"""Callable that takes a market_id and returns the resolution YES price (0 or 1) or None if unresolved."""


class SettlementWatcher:
    def __init__(
        self,
        get_open_trades: Callable[[], Awaitable[list[Trade]]],
        resolve: ResolveFn,
        on_settled: Callable[[Trade, float, float], Awaitable[None]],
        interval_seconds: float = 60.0,
    ) -> None:
        self._get_open = get_open_trades
        self._resolve = resolve
        self._on_settled = on_settled
        self._interval = interval_seconds

    async def tick(self) -> int:
        """Poll once; return number of trades settled this tick."""
        trades = await self._get_open()
        settled = 0
        for trade in trades:
            try:
                resolution = await self._resolve(trade.market_id)
            except Exception as e:
                log.warning("settlement.resolve_failed", market=trade.market_id, error=str(e))
                continue
            if resolution is None:
                continue
            payoff_for_side = (
                resolution if trade.direction == "YES" else 1.0 - resolution
            )
            cost = trade.fill_price or trade.entry_price or 0.0
            if cost <= 0:
                pnl = 0.0
            else:
                contracts = trade.size_usdc / cost
                pnl = (payoff_for_side - cost) * contracts
            try:
                await self._on_settled(trade, payoff_for_side, pnl)
                settled += 1
            except Exception as e:
                log.exception(
                    "settlement.on_settled_failed",
                    trade_id=trade.trade_id,
                    error=str(e),
                )
        return settled

    async def run_forever(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception as e:
                log.exception("settlement.tick_failed", error=str(e))
            await asyncio.sleep(self._interval)
