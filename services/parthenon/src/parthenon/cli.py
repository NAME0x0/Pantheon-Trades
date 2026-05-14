"""Parthenon CLI — health probes and one-shot archive of a thesis bundle.

Most archive work runs inline inside the Boule consumer; this CLI is the
manual escape hatch (e.g. archive a single thesis_id from the DB after a
service crash, or re-anchor a manifest whose tx never confirmed).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

import structlog

from parthenon.anchor import AnchorService
from parthenon.ipfs import IpfsClient
from parthenon.replay import replay_thesis

log = structlog.get_logger("parthenon.cli")


async def health() -> None:
    ipfs = IpfsClient.from_env()
    try:
        # Pin a tiny payload to confirm the daemon answers.
        cid = await ipfs.add_json({"hello": "parthenon"}, pin=False)
        print(f"ipfs ok: probe cid {cid}")
    finally:
        await ipfs.close()
    rpc = os.environ.get("RPC_URL", "https://rpc.testnet.arc.network")
    print(f"rpc_url: {rpc}")
    print(f"registry: {os.environ.get('PARTHENON_REGISTRY_ADDRESS', '(unset)')}")


async def replay(manifest_cid: str) -> None:
    ipfs = IpfsClient.from_env()
    try:
        bundle = await replay_thesis(ipfs, manifest_cid)
        print(json.dumps(bundle, indent=2, default=str))
    finally:
        await ipfs.close()


async def anchor(manifest_cid: str, merkle_root: str, kind: str) -> None:
    receipt = await AnchorService().anchor(
        manifest_cid=manifest_cid, merkle_root=merkle_root, kind=kind
    )
    print(json.dumps({"tx": receipt.tx_hash, "block": receipt.block_number}, indent=2))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="parthenon")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health", help="Probe IPFS + RPC")

    rp = sub.add_parser("replay", help="Replay an archived thesis bundle")
    rp.add_argument("manifest_cid")

    ap = sub.add_parser("anchor", help="Anchor a (manifest_cid, root) pair on Arc")
    ap.add_argument("manifest_cid")
    ap.add_argument("merkle_root")
    ap.add_argument("--kind", default="thesis")

    args = parser.parse_args()
    if args.cmd == "health":
        asyncio.run(health())
    elif args.cmd == "replay":
        asyncio.run(replay(args.manifest_cid))
    elif args.cmd == "anchor":
        asyncio.run(anchor(args.manifest_cid, args.merkle_root, args.kind))


if __name__ == "__main__":
    main()
