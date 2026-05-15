"""Pythia CLI — probes data sources or runs the cache-warming loop."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

import httpx
import structlog

from pythia.health import health_for, overall_health
from pythia.polymarket import PolymarketSource

log = structlog.get_logger("pythia.cli")


async def health() -> None:
    http = httpx.AsyncClient(timeout=10.0)
    try:
        sources = [PolymarketSource(http)]
        for s in sources:
            await s.get()
        report = health_for(sources)
        print(
            json.dumps(
                {
                    "overall": overall_health(report),
                    "sources": [
                        {
                            "source": e.source,
                            "fresh": e.fresh,
                            "staleness_seconds": e.staleness_seconds,
                            "max_staleness_seconds": e.max_staleness_seconds,
                        }
                        for e in report
                    ],
                },
                indent=2,
            )
        )
    finally:
        await http.aclose()


async def serve(interval: float) -> None:
    http = httpx.AsyncClient(timeout=15.0)
    sources = [PolymarketSource(http)]
    log.info("pythia.cli.serve", interval=interval)
    try:
        while True:
            for s in sources:
                try:
                    await s.get(force=True)
                except Exception as e:  # noqa: BLE001
                    log.warning("pythia.cli.fetch_failed", source=s.name, error=str(e))
            await asyncio.sleep(interval)
    finally:
        await http.aclose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="pythia")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="Probe configured data sources")
    sp = sub.add_parser("serve", help="Cache-warming loop")
    sp.add_argument("--interval", type=float, default=30.0)
    args = parser.parse_args()
    if args.cmd == "health":
        asyncio.run(health())
    elif args.cmd == "serve":
        asyncio.run(serve(interval=args.interval))


if __name__ == "__main__":
    main()
