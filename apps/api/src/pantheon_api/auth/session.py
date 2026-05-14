"""Session token issuance/verification — itsdangerous-signed JSON.

We keep the session token small (address + roles + iat/exp) and rely on
``itsdangerous`` for HMAC integrity. JWT-style ``python-jose`` is available
in the dep set, but we deliberately use the simpler signer to keep the
token compact and rotation trivial (just bump ``secret_key``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from pantheon_core.schema import utc_now

DEFAULT_TTL_SECONDS = 24 * 3600


@dataclass
class SessionPayload:
    address: str
    roles: list[str] = field(default_factory=list)
    issued_at: datetime = field(default_factory=utc_now)
    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(seconds=DEFAULT_TTL_SECONDS))

    def to_json(self) -> str:
        return json.dumps(
            {
                "address": self.address,
                "roles": self.roles,
                "iat": int(self.issued_at.timestamp()),
                "exp": int(self.expires_at.timestamp()),
            },
            separators=(",", ":"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionPayload":
        return cls(
            address=data["address"],
            roles=list(data.get("roles", [])),
            issued_at=datetime.fromtimestamp(int(data["iat"])).astimezone(),
            expires_at=datetime.fromtimestamp(int(data["exp"])).astimezone(),
        )


def issue_session(payload: SessionPayload, secret: str) -> str:
    signer = TimestampSigner(secret)
    return signer.sign(payload.to_json()).decode("utf-8")


def decode_session(token: str, secret: str, max_age: int = DEFAULT_TTL_SECONDS) -> SessionPayload | None:
    signer = TimestampSigner(secret)
    try:
        raw = signer.unsign(token, max_age=max_age).decode("utf-8")
    except (SignatureExpired, BadSignature):
        return None
    try:
        return SessionPayload.from_dict(json.loads(raw))
    except (KeyError, ValueError, json.JSONDecodeError):
        return None
