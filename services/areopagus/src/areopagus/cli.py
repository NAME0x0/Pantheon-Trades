"""Areopagus CLI — runs the boule:theses gating consumer."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

from areopagus.consumer import consume_forever


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="areopagus")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="Run the boule:theses gating consumer")
    serve.add_argument(
        "--consumer-name",
        default=os.environ.get("HOSTNAME", "areopagus-1"),
    )
    args = parser.parse_args()
    if args.cmd == "serve":
        asyncio.run(consume_forever(consumer_name=args.consumer_name))


if __name__ == "__main__":
    main()
