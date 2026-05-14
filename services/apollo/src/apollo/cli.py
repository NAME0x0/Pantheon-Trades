"""Apollo CLI — ``python -m apollo.cli serve`` runs the scanner loop."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from collections.abc import Awaitable, Callable

import httpx
import redis.asyncio as aioredis
import structlog

from apollo.runner import ApolloRunner
from apollo.scorer import MarketSnapshot
from apollo.sources.polymarket import snapshot_from_market_payload

log = structlog.get_logger("apollo.cli")

POLYMARKET_HOST = "https://clob.polymarket.com"
DEFAULT_INTERVAL = float(os.environ.get("APOLLO_INTERVAL", "30"))
DEFAULT_LIMIT = int(os.environ.get("APOLLO_MARKET_LIMIT", "50"))


async def _fetch_markets(http: httpx.AsyncClient, limit: int) -> list[dict]:
    try:
        resp = await http.get(
            f"{POLYMARKET_HOST}/markets",
            params={"limit": limit},
            timeout=15.0,
        )
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPError as e:
        log.warning("apollo.cli.market_fetch_failed", error=str(e))
        return []
    if isinstance(payload, dict):
        markets = payload.get("data") or payload.get("markets") or []
    else:
        markets = payload or []
    return list(markets)[:limit]


def _make_source(http: httpx.AsyncClient, limit: int) -> Callable[[], Awaitable[list[MarketSnapshot]]]:
    async def source() -> list[MarketSnapshot]:
        markets = await _fetch_markets(http, limit)
        out: list[MarketSnapshot] = []
        for m in markets:
            try:
                out.append(snapshot_from_market_payload(m))
            except Exception as e:  # noqa: BLE001
                log.warning("apollo.cli.snapshot_failed", error=str(e))
        return out

    return source


async def serve(interval: float = DEFAULT_INTERVAL, limit: int = DEFAULT_LIMIT) -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis = await aioredis.from_url(redis_url, decode_responses=True)
    http = httpx.AsyncClient()
    runner = ApolloRunner(source=_make_source(http, limit), redis=redis)
    log.info("apollo.cli.serve", interval=interval, limit=limit)
    try:
        # Embed publish in the loop so a stream-cached signal payload is
        # available for downstream consumers via apollo:signal:<id>.
        while True:
            try:
                signals = await runner.scan_once()
                for sig in signals:
                    await runner.publish(sig)
                    await redis.setex(
                        f"apollo:signal:{sig.signal_id}", 3_600, sig.model_dump_json()
                    )
                    await redis.setex(
                        f"boule:signal:{sig.signal_id}", 86_400, sig.model_dump_json()
                    )
            except Exception as e:  # noqa: BLE001
                log.exception("apollo.cli.scan_failed", error=str(e))
            await asyncio.sleep(interval)
    finally:
        await http.aclose()
        await redis.aclose()


async def scan_once(limit: int = DEFAULT_LIMIT) -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    redis = await aioredis.from_url(redis_url, decode_responses=True)
    http = httpx.AsyncClient()
    runner = ApolloRunner(source=_make_source(http, limit), redis=redis)
    try:
        signals = await runner.scan_once()
        for sig in signals:
            await runner.publish(sig)
        print(json.dumps({"published": [s.signal_id for s in signals]}, indent=2))
    finally:
        await http.aclose()
        await redis.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="apollo")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve_p = sub.add_parser("serve", help="Run the signal-scoring loop")
    serve_p.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    serve_p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    once_p = sub.add_parser("scan", help="Scan once and exit")
    once_p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    args = parser.parse_args()
    if args.cmd == "serve":
        asyncio.run(serve(interval=args.interval, limit=args.limit))
    else:
        asyncio.run(scan_once(limit=args.limit))


if __name__ == "__main__":
    main()
