"""ERC-8004 passport client — read/write agent passports to the Arc registry.

Tries to stay minimal: ``mint``, ``update``, ``get``. The contract enforces
ownership and version monotonicity; we just sign and submit.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import structlog

from parthenon.passport import Passport

log = structlog.get_logger("parthenon.erc8004")


@dataclass
class Erc8004Config:
    rpc_url: str
    chain_id: int
    private_key: str
    registry_address: str


class Erc8004Client:
    def __init__(self, config: Erc8004Config | None = None) -> None:
        self._config = config or Erc8004Config(
            rpc_url=os.environ.get("RPC_URL", "https://rpc.testnet.arc.network"),
            chain_id=int(os.environ.get("CHAIN_ID", "5042002")),
            private_key=os.environ["PRIVATE_KEY"],
            registry_address=os.environ["ERC8004_REGISTRY_ADDRESS"],
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
            abi=_ERC8004_ABI,
        )
        return self._contract

    async def mint(self, passport: Passport) -> str:
        return await asyncio.to_thread(self._mint_sync, passport)

    def _mint_sync(self, passport: Passport) -> str:
        contract = self._ensure()
        w3 = self._w3
        tx = contract.functions.mint(
            passport.agent_id,
            passport.version,
            passport.metadata_cid,
            passport.skills,
        ).build_transaction(
            {
                "from": self._account.address,
                "nonce": w3.eth.get_transaction_count(self._account.address),
                "chainId": self._config.chain_id,
                "gas": 300_000,
                "maxFeePerGas": w3.to_wei(50, "gwei"),
                "maxPriorityFeePerGas": w3.to_wei(2, "gwei"),
            }
        )
        signed = self._account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()
        log.info("parthenon.erc8004.mint", agent=passport.agent_id, tx=tx_hash)
        return tx_hash

    async def get(self, agent_id: str) -> dict:
        return await asyncio.to_thread(self._get_sync, agent_id)

    def _get_sync(self, agent_id: str) -> dict:
        contract = self._ensure()
        version, metadata_cid, skills, issuer = contract.functions.get(agent_id).call()
        return {
            "agent_id": agent_id,
            "version": int(version),
            "metadata_cid": metadata_cid,
            "skills": list(skills),
            "issuer": issuer,
        }


_ERC8004_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "string"},
            {"name": "version", "type": "uint256"},
            {"name": "metadataCid", "type": "string"},
            {"name": "skills", "type": "string[]"},
        ],
        "name": "mint",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "string"}],
        "name": "get",
        "outputs": [
            {"name": "version", "type": "uint256"},
            {"name": "metadataCid", "type": "string"},
            {"name": "skills", "type": "string[]"},
            {"name": "issuer", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]
