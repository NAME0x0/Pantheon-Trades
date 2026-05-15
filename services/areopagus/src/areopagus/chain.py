"""On-chain witness writer for ProofOfRestraint.

When Areopagus rejects a thesis post-deliberation, this module fires a
``declineTrade(bytes32,string,string,string)`` transaction at the deployed
``ProofOfRestraint`` contract on Arc Testnet. The Redis stream remains the
source of truth — chain writes are best-effort, fire-and-forget, and never
block the consumer loop.

Disabled until ``PROOF_OF_RESTRAINT_ADDRESS`` is set in the environment.
That keeps unit tests and local dev runs from hitting the network.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import structlog

from areopagus.proof_of_restraint import ProofOfRestraint

log = structlog.get_logger("areopagus.chain")


PROOF_OF_RESTRAINT_ABI = [
    {
        "type": "function",
        "name": "declineTrade",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "signalHash", "type": "bytes32"},
            {"name": "marketId", "type": "string"},
            {"name": "reasonCode", "type": "string"},
            {"name": "note", "type": "string"},
        ],
        "outputs": [{"name": "proofId", "type": "uint256"}],
    },
    {
        "type": "function",
        "name": "nextProofId",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"type": "uint256"}],
    },
]


@dataclass
class ChainWriteResult:
    tx_hash: str
    proof_id: Optional[int]
    explorer_url: Optional[str]


class RestraintChainWriter:
    """Async ProofOfRestraint contract writer.

    Construct once at consumer startup, reuse across many emit calls. The
    Web3 client is created lazily on first send so the consumer can still
    boot when the chain is unreachable.
    """

    def __init__(
        self,
        rpc_url: str,
        contract_address: str,
        private_key: str,
        chain_id: int,
        explorer_base: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._rpc_url = rpc_url
        self._contract_address = contract_address
        self._private_key = private_key
        self._chain_id = chain_id
        self._explorer_base = explorer_base
        self._timeout = timeout_seconds
        self._w3 = None
        self._contract = None
        self._account = None
        self._lock = asyncio.Lock()  # serialise nonce + tx sign

    @classmethod
    def from_env(cls) -> "RestraintChainWriter | None":
        address = os.environ.get("PROOF_OF_RESTRAINT_ADDRESS", "").strip()
        rpc = os.environ.get("RPC_URL", "").strip()
        pk = os.environ.get("PRIVATE_KEY", "").strip()
        chain_id = int(os.environ.get("CHAIN_ID", "5042002"))
        explorer = os.environ.get("ARC_EXPLORER_URL", "").strip() or None
        if not address or not rpc or not pk:
            return None
        return cls(
            rpc_url=rpc,
            contract_address=address,
            private_key=pk,
            chain_id=chain_id,
            explorer_base=explorer,
        )

    async def _ensure_client(self) -> None:
        if self._w3 is not None:
            return
        # Lazy imports keep the dependency optional for dev runs.
        from web3 import AsyncHTTPProvider, AsyncWeb3
        from eth_account import Account

        self._w3 = AsyncWeb3(AsyncHTTPProvider(self._rpc_url, request_kwargs={"timeout": self._timeout}))
        self._account = Account.from_key(self._private_key)
        self._contract = self._w3.eth.contract(
            address=self._w3.to_checksum_address(self._contract_address),
            abi=PROOF_OF_RESTRAINT_ABI,
        )

    async def write(self, proof: ProofOfRestraint) -> ChainWriteResult | None:
        """Submit a single declineTrade tx.

        Returns the receipt tuple on success, or ``None`` on any failure
        (logged but never raised — Redis remains the source of truth).
        """
        try:
            await self._ensure_client()
            assert self._w3 is not None and self._contract is not None and self._account is not None

            signal_hash_bytes = bytes.fromhex(proof.signal_hash.removeprefix("0x"))
            if len(signal_hash_bytes) != 32:
                log.warning(
                    "areopagus.chain.bad_signal_hash",
                    proof_id=proof.proof_id,
                    length=len(signal_hash_bytes),
                )
                return None

            async with self._lock:
                nonce = await self._w3.eth.get_transaction_count(self._account.address, "pending")
                # Modest cap — declineTrade is ~100k gas.
                gas_price = await self._w3.eth.gas_price
                tx = await self._contract.functions.declineTrade(
                    signal_hash_bytes,
                    proof.market_id,
                    proof.reason_code,
                    proof.note,
                ).build_transaction(
                    {
                        "from": self._account.address,
                        "nonce": nonce,
                        "chainId": self._chain_id,
                        "gas": 300_000,
                        "gasPrice": gas_price,
                    }
                )
                signed = self._account.sign_transaction(tx)
                tx_hash = await self._w3.eth.send_raw_transaction(signed.raw_transaction)

            tx_hash_hex = tx_hash.hex() if isinstance(tx_hash, (bytes, bytearray)) else str(tx_hash)
            if not tx_hash_hex.startswith("0x"):
                tx_hash_hex = "0x" + tx_hash_hex

            # Best-effort receipt wait — bounded so we don't pin the event loop.
            proof_id: int | None = None
            try:
                receipt = await asyncio.wait_for(
                    self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30),
                    timeout=35,
                )
                if receipt.status == 1:
                    proof_id = int(receipt.logs[0].topics[1].hex(), 16) if receipt.logs else None
                else:
                    log.warning(
                        "areopagus.chain.tx_reverted",
                        tx_hash=tx_hash_hex,
                        proof_id=proof.proof_id,
                    )
            except (asyncio.TimeoutError, Exception) as wait_err:  # noqa: BLE001
                log.info(
                    "areopagus.chain.tx_submitted_no_receipt",
                    tx_hash=tx_hash_hex,
                    proof_id=proof.proof_id,
                    reason=str(wait_err),
                )

            explorer_url = (
                f"{self._explorer_base.rstrip('/')}/tx/{tx_hash_hex}"
                if self._explorer_base
                else None
            )
            log.info(
                "areopagus.chain.proof_anchored",
                proof_id=proof.proof_id,
                onchain_proof_id=proof_id,
                tx_hash=tx_hash_hex,
                signal_hash=proof.signal_hash,
                market_id=proof.market_id,
                reason=proof.reason_code,
                explorer=explorer_url,
            )
            return ChainWriteResult(
                tx_hash=tx_hash_hex,
                proof_id=proof_id,
                explorer_url=explorer_url,
            )
        except Exception as e:  # noqa: BLE001
            log.warning(
                "areopagus.chain.write_failed",
                proof_id=proof.proof_id,
                error=str(e),
            )
            return None

    async def close(self) -> None:
        if self._w3 is None:
            return
        try:
            await self._w3.provider.disconnect()
        except Exception:  # noqa: BLE001
            pass
