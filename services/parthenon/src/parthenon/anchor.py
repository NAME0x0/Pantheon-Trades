"""On-chain anchor — posts archive Merkle roots to Arc Testnet.

The anchor's only job is to write ``(manifest_cid, merkle_root, kind)``
tuples to the Parthenon registry contract. We deliberately keep the
calldata minimal: the manifest holds the full archive metadata, the root
proves any artifact derived from that manifest, and the kind tag makes
indexers cheap.

Failure to anchor is *not* fatal — the off-chain archive is still durable.
We surface anchor failures as a structured warning and let the caller
decide whether to retry.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import structlog

log = structlog.get_logger("parthenon.anchor")


@dataclass
class AnchorReceipt:
    tx_hash: str
    block_number: int | None
    manifest_cid: str
    merkle_root: str


@dataclass
class AnchorConfig:
    rpc_url: str
    chain_id: int
    private_key: str
    registry_address: str


class AnchorService:
    """Submits Merkle roots and CIDs to the Parthenon registry on Arc."""

    def __init__(self, config: AnchorConfig | None = None) -> None:
        self._config = config or AnchorConfig(
            rpc_url=os.environ.get("RPC_URL", "https://rpc.testnet.arc.network"),
            chain_id=int(os.environ.get("CHAIN_ID", "5042002")),
            private_key=os.environ["PRIVATE_KEY"],
            registry_address=os.environ["PARTHENON_REGISTRY_ADDRESS"],
        )
        self._w3: Any = None
        self._account: Any = None
        self._contract: Any = None

    def _ensure(self) -> Any:
        if self._w3 is not None:
            return self._contract
        from web3 import Web3
        from eth_account import Account  # noqa: WPS433
        self._w3 = Web3(Web3.HTTPProvider(self._config.rpc_url))
        self._account = Account.from_key(self._config.private_key)
        self._contract = self._w3.eth.contract(
            address=Web3.to_checksum_address(self._config.registry_address),
            abi=_REGISTRY_ABI,
        )
        return self._contract

    async def anchor(
        self,
        manifest_cid: str,
        merkle_root: str,
        kind: str = "thesis",
    ) -> AnchorReceipt:
        # web3.py is sync; run in a thread so the event loop stays alive.
        import asyncio
        return await asyncio.to_thread(self._anchor_sync, manifest_cid, merkle_root, kind)

    def _anchor_sync(self, manifest_cid: str, merkle_root: str, kind: str) -> AnchorReceipt:
        contract = self._ensure()
        w3 = self._w3
        nonce = w3.eth.get_transaction_count(self._account.address)
        root_bytes = bytes.fromhex(merkle_root[2:] if merkle_root.startswith("0x") else merkle_root)
        tx = contract.functions.anchor(
            kind,
            manifest_cid,
            root_bytes,
        ).build_transaction(
            {
                "from": self._account.address,
                "nonce": nonce,
                "chainId": self._config.chain_id,
                "gas": 200_000,
                "maxFeePerGas": w3.to_wei(50, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        log.info(
            "parthenon.anchored",
            tx_hash=receipt.transactionHash.hex(),
            block=receipt.blockNumber,
            kind=kind,
            manifest_cid=manifest_cid,
        )
        return AnchorReceipt(
            tx_hash=receipt.transactionHash.hex(),
            block_number=receipt.blockNumber,
            manifest_cid=manifest_cid,
            merkle_root=merkle_root,
        )


_REGISTRY_ABI = [
    {
        "inputs": [
            {"name": "kind", "type": "string"},
            {"name": "manifestCid", "type": "string"},
            {"name": "merkleRoot", "type": "bytes32"},
        ],
        "name": "anchor",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]
