"""End-to-end Arc Testnet smoke test.

Exercises the project's web3 wiring against the live Arc Testnet RPC:

  1. Loads settings via the project's pantheon_api.config so the same
     code path that the FastAPI gateway uses is what we test.
  2. Connects via web3.py and verifies chain id + block number.
  3. Reads the USDC system contract (0x3600...000) at Arc's well-known
     address — Arc makes USDC native, so a working USDC ERC-20 view is
     the strongest single signal that the chain is healthy.
  4. Round-trips a sample Signal through pantheon_core.schema +
     parthenon.hash (keccak content hash) to prove the off-chain hashing
     matches what an on-chain anchor would receive.
  5. Verifies parthenon.anchor.AnchorService can construct its config
     from environment variables without raising.

No private key, no transaction signing, no funds spent. The script
exits non-zero on any failure so CI can gate on it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "pantheon-core" / "src"))
sys.path.insert(0, str(ROOT / "services" / "parthenon" / "src"))


# Arc Testnet's native-USDC system contract.
USDC_ADDRESS = "0x3600000000000000000000000000000000000000"

USDC_ABI = [
    {
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _hr(title: str) -> None:
    print(f"\n----- {title} -----")


def step_rpc() -> tuple[int, int]:
    from pantheon_api.config import settings
    from web3 import Web3

    _hr("RPC")
    print(f"rpc_url      = {settings.rpc_url}")
    print(f"arc_chain_id = {settings.arc_chain_id}")

    w3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 10}))
    assert w3.is_connected(), f"RPC unreachable: {settings.rpc_url}"

    chain_id = w3.eth.chain_id
    block = w3.eth.block_number
    gas_price = w3.eth.gas_price

    assert chain_id == settings.arc_chain_id, (
        f"chain id mismatch: project expects {settings.arc_chain_id}, "
        f"network reports {chain_id}"
    )

    print(f"chain_id     = {chain_id}")
    print(f"latest_block = {block:,}")
    print(f"gas_price    = {gas_price:,} wei  ({gas_price / 1e9:.2f} gwei)")
    return chain_id, block


def step_usdc() -> None:
    from pantheon_api.config import settings
    from web3 import Web3

    _hr("USDC system contract")
    w3 = Web3(Web3.HTTPProvider(settings.rpc_url, request_kwargs={"timeout": 10}))
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_ADDRESS), abi=USDC_ABI)

    name = usdc.functions.name().call()
    symbol = usdc.functions.symbol().call()
    decimals = usdc.functions.decimals().call()
    supply = usdc.functions.totalSupply().call()

    print(f"address  = {USDC_ADDRESS}")
    print(f"name     = {name}")
    print(f"symbol   = {symbol}")
    print(f"decimals = {decimals}")
    print(f"supply   = {supply:,} ({supply / 10**decimals:,.2f} {symbol})")

    assert symbol.upper() in ("USDC", "USD COIN"), f"unexpected USDC symbol: {symbol}"


def step_hashing() -> None:
    from datetime import datetime, timezone

    from pantheon_core.schema import Signal
    from parthenon.hash import content_hash, sha256_hex, thesis_hash
    from parthenon.merkle import build_merkle_tree, merkle_proof, verify_proof

    _hr("schema + hashing round-trip")

    sig = Signal(
        market_id="0xprobe",
        question="Does the Arc probe round-trip?",
        category="other",
        market_probability=0.42,
        oracle_probability=0.55,
        edge=0.13,
        edge_abs=0.13,
        band="A",
        band_score=0.78,
        liquidity_score=0.81,
        volatility_score=0.4,
        catalyst_score=0.6,
        sentiment_score=0.55,
        correlation_score=0.7,
        trend_score=0.6,
        volume_24h=100_000,
        open_interest=250_000,
        bid=0.41,
        ask=0.43,
        spread=0.02,
        data_sources=["arc_probe"],
        staleness_seconds=10,
        source_trust_score=1.0,
        pythia_snapshot_at=datetime.now(timezone.utc),
    )

    payload = sig.model_dump(mode="json")
    k = content_hash(payload)
    s = sha256_hex(payload)
    th = thesis_hash("thesis-0", sig.market_id, sig.oracle_probability, "YES")

    print(f"keccak content_hash = {k}")
    print(f"sha256 content_hash = {s}")
    print(f"thesis_hash         = {th}")

    assert k.startswith("0x") and len(k) == 66
    assert s.startswith("0x") and len(s) == 66

    leaves = [k, s, th]
    root, layers = build_merkle_tree(leaves)
    for idx, leaf in enumerate(leaves):
        proof = merkle_proof(layers, idx)
        assert verify_proof(leaf, proof, root), f"merkle proof failed for leaf {idx}"
    print(f"merkle_root         = {root}")
    print("merkle proof for 3 leaves verified")


def step_anchor_config() -> None:
    from parthenon.anchor import AnchorConfig
    from parthenon.erc8004_client import Erc8004Config

    _hr("anchor service config (no signing)")

    # Use sentinel env values; do not sign or submit anything.
    os.environ.setdefault("PRIVATE_KEY", "0x" + "11" * 32)
    os.environ.setdefault("PARTHENON_REGISTRY_ADDRESS", "0x" + "ab" * 20)
    os.environ.setdefault("ERC8004_REGISTRY_ADDRESS", "0x" + "cd" * 20)
    os.environ.setdefault("CHAIN_ID", "5042002")

    a = AnchorConfig(
        rpc_url=os.environ.get("RPC_URL", "https://rpc.testnet.arc.network"),
        chain_id=int(os.environ["CHAIN_ID"]),
        private_key=os.environ["PRIVATE_KEY"],
        registry_address=os.environ["PARTHENON_REGISTRY_ADDRESS"],
    )
    e = Erc8004Config(
        rpc_url=os.environ.get("RPC_URL", "https://rpc.testnet.arc.network"),
        chain_id=int(os.environ["CHAIN_ID"]),
        private_key=os.environ["PRIVATE_KEY"],
        registry_address=os.environ["ERC8004_REGISTRY_ADDRESS"],
    )
    print(f"AnchorConfig    chain_id={a.chain_id} registry={a.registry_address}")
    print(f"Erc8004Config   chain_id={e.chain_id} registry={e.registry_address}")
    assert a.chain_id == 5042002 and e.chain_id == 5042002


def main() -> int:
    try:
        step_rpc()
        step_usdc()
        step_hashing()
        step_anchor_config()
    except AssertionError as e:
        print(f"\nFAIL: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e!r}")
        return 2
    print("\nArc Testnet probe OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
