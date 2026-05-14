"""Boule CLI — ``python -m boule.cli serve`` runs the deliberation consumer."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

import structlog

from boule.consumer import consume_forever

log = structlog.get_logger("boule.cli")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="boule")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="Run the apollo:signals consumer")
    serve.add_argument(
        "--consumer-name",
        default=os.environ.get("HOSTNAME", "boule-1"),
        help="Redis consumer group member name",
    )
    args = parser.parse_args()
    if args.cmd == "serve":
        asyncio.run(consume_forever(consumer_name=args.consumer_name))


if __name__ == "__main__":
    main()
