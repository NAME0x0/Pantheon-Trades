"""Strategos CLI — routes approval tokens through paper/live execution."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

from strategos.consumer import consume_forever


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="strategos")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="Run the approval consumer")
    serve.add_argument(
        "--consumer-name",
        default=os.environ.get("HOSTNAME", "strategos-1"),
    )
    args = parser.parse_args()
    if args.cmd == "serve":
        asyncio.run(consume_forever(consumer_name=args.consumer_name))


if __name__ == "__main__":
    main()
