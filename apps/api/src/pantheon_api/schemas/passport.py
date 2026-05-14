"""ERC-8004 passport response shape."""

from __future__ import annotations

from pydantic import BaseModel


class PassportSummary(BaseModel):
    agent_id: str
    version: int
    metadata_cid: str
    skills: list[str]
    issuer: str
