"""Agent identity helpers — keystore wrappers used when issuing passports."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    address: str
    private_key: str

    @classmethod
    def from_env(cls, agent_id: str) -> "AgentIdentity":
        key_env = f"AGENT_{agent_id.upper()}_PRIVATE_KEY"
        pk = os.environ.get(key_env)
        if not pk:
            raise RuntimeError(f"{key_env} not set")
        from eth_account import Account

        acct = Account.from_key(pk)
        return cls(agent_id=agent_id, address=acct.address, private_key=pk)
