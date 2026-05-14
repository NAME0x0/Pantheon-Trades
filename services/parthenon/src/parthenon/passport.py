"""ERC-8004 agent passport schema and serialisation.

A passport is the portable, on-chain-registered identity for one Boule
council agent. It carries:

  * agent_id  — stable string slug (e.g., "ares")
  * version   — bumped on each material capability change
  * metadata_cid — IPFS CID of the agent's prompt + config + scoring history
  * skills    — terse list of capability tags ("bull_advocate", "risk_veto")
  * issuer    — Pantheon Olympus signing address that authored the passport
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from pantheon_core.schema import utc_now


class Passport(BaseModel):
    agent_id: str
    version: int = 1
    metadata_cid: str
    skills: list[str] = Field(default_factory=list)
    issuer: str
    issued_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    signature: str | None = None

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.expires_at is None:
            return False
        return (now or utc_now()) >= self.expires_at
