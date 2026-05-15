from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime

from pantheon_core.schema import utc_now


@dataclass
class ProofOfRestraint:
    """
    On-chain proof that a signal was observed but trade was declined.
    Submitted to NoTradeAlpha.sol on Arc Testnet.
    """
    proof_id: str
    signal_id: str
    market_id: str
    reason_code: str
    note: str
    signal_hash: str
    created_at: datetime

    @classmethod
    def create(cls, signal_id: str, market_id: str, signal_json: str, reason_code: str, note: str) -> "ProofOfRestraint":
        signal_hash = "0x" + hashlib.sha256(signal_json.encode()).hexdigest()
        return cls(
            proof_id=str(uuid.uuid4()),
            signal_id=signal_id,
            market_id=market_id,
            reason_code=reason_code,
            note=note,
            signal_hash=signal_hash,
            created_at=utc_now(),
        )

    def to_calldata(self) -> dict:
        """Matches `ProofOfRestraint.declineTrade(bytes32, string, string, string)`."""
        return {
            "signalHash": self.signal_hash,
            "marketId": self.market_id,
            "reasonCode": self.reason_code,
            "note": self.note,
        }
