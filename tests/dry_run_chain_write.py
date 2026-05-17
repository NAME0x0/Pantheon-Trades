"""Dry-run the Areopagus → ProofOfRestraint chain write against Arc Testnet.

Builds a real ProofOfRestraint payload (curated restraint scenario), calls
``RestraintChainWriter.write(proof)`` exactly the way the consumer would,
and prints the resulting Arcscan link.

    uv run python tests/dry_run_chain_write.py

Requires ``PROOF_OF_RESTRAINT_ADDRESS``, ``RPC_URL``, and ``PRIVATE_KEY``
in .env (deployer wallet must hold RESTRAINT_ROLE on the deployed
contract — auto-granted at construct time).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "areopagus" / "src",
):
    sys.path.insert(0, str(p))


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ[key.strip()] = value.strip()


async def main() -> int:
    _load_env(ROOT / ".env")

    from areopagus.chain import RestraintChainWriter
    from areopagus.proof_of_restraint import ProofOfRestraint

    writer = RestraintChainWriter.from_env()
    if writer is None:
        print("FAIL RestraintChainWriter.from_env() returned None")
        print("  Required: PROOF_OF_RESTRAINT_ADDRESS, RPC_URL, PRIVATE_KEY")
        return 1

    print("=== Arc Testnet dry-run ===")
    print(f"  contract     : {writer._contract_address}")
    print(f"  rpc          : {writer._rpc_url}")
    print(f"  chain_id     : {writer._chain_id}")
    print(f"  explorer     : {writer._explorer_base or '(none)'}")

    proof = ProofOfRestraint.create(
        signal_id="dry-run-sig-001",
        market_id="0xpantheon_demo_btc_120k",
        signal_json='{"market_id":"0xpantheon_demo_btc_120k","oracle_probability":0.59,"market_probability":0.42,"edge":0.17}',
        reason_code="ZEUS_VETO",
        note=f"dry-run from tests/dry_run_chain_write.py at {datetime.now(timezone.utc).isoformat()}",
    )

    print("\nproof bundle:")
    print(f"  proof_id     : {proof.proof_id}")
    print(f"  signal_hash  : {proof.signal_hash}")
    print(f"  market       : {proof.market_id}")
    print(f"  reason       : {proof.reason_code}")
    print(f"  note         : {proof.note[:80]}")

    print("\nfiring declineTrade(...)...")
    result = await writer.write(proof)
    await writer.close()

    if result is None:
        print("\nFAIL chain write returned None — check logs above")
        return 1

    print("\nOK on-chain witness landed")
    print(f"  tx_hash          : {result.tx_hash}")
    print(f"  onchain proof_id : {result.proof_id}")
    print(f"  explorer         : {result.explorer_url}")
    print("\nThis is the flagship feature firing live on Arc Testnet.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
