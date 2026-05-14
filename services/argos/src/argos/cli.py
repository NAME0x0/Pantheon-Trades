"""Argos CLI — runs the position monitor loop.

Reads open trades from ``strategos:trades`` (caches them keyed by trade_id)
and polls Polymarket for the YES-side price every ``--interval`` seconds,
publishing ExitSignals when a rule fires.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import Trade

from argos.heartbeat import write_heartbeat
from argos.monitor import ArgosMonitor
from argos.pnl import Position

log = structlog.get_logger("argos.cli")

POLYMARKET_HOST = "https://clob.polymarket.com"


async def _hydrate_positions(redis: aioredis.Redis) -> list[Position]:
    """Build live positions from cached Strategos trades."""
    keys = [k async for k in redis.scan_iter(match="strategos:trade:*", count=200)]
    positions: list[Position] = []
    for k in keys:
        raw = await redis.get(k)
        if not raw:
            continue
        try:
            trade = Trade.model_validate_json(raw)
        except Exception:
            continue
        if trade.status not in ("filled", "partial"):
            continue
        entry = trade.fill_price or trade.entry_price
        if not entry or entry <= 0:
            continue
        positions.append(
            Position(
                trade_id=trade.trade_id,
                market_id=trade.market_id,
                direction=trade.direction,
                entry_price=entry,
                size_usdc=trade.size_usdc,
                entered_at=trade.fill_time or trade.created_at,
                target=min(entry + 0.15, 0.95),
                stop=max(entry - 0.10, 0.05),
            )
        )
    return positions


def _make_price_fetcher(http: httpx.AsyncClient):
    async def fetch(market_id: str) -> float | None:
        try:
            resp = await http.get(f"{POLYMARKET_HOST}/markets/{market_id}", timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError:
            return None
        price = data.get("last_trade_price") or data.get("lastTradePrice")
        if price is None:
            return None
        try:
            return float(price)
        except (TypeError, ValueError):
            return None
    return fetch


async def serve(interval: float) -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis = await aioredis.from_url(redis_url, decode_responses=True)
    http = httpx.AsyncClient()

    async def get_positions():
        return await _hydrate_positions(redis)

    monitor = ArgosMonitor(
        get_positions=get_positions,
        get_yes_price=_make_price_fetcher(http),
        redis=redis,
        interval_seconds=interval,
    )

    async def heartbeat_loop():
        while True:
            await write_heartbeat(redis)
            await asyncio.sleep(15)

    log.info("argos.cli.serve", interval=interval)
    try:
        await asyncio.gather(monitor.run_forever(), heartbeat_loop())
    finally:
        await http.aclose()
        await redis.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="argos")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("serve", help="Run the monitor loop")
    sp.add_argument("--interval", type=float, default=15.0)
    args = parser.parse_args()
    if args.cmd == "serve":
        asyncio.run(serve(interval=args.interval))


if __name__ == "__main__":
    main()
