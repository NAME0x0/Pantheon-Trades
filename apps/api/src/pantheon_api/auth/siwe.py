"""Sign-In With Ethereum verification.

Two-step flow:
  1. Client requests a nonce via ``/auth/nonce`` keyed by their address.
  2. Client signs a SIWE message containing that nonce and POSTs the
     message + signature; we verify, consume the nonce, and issue a
     session token.

We use the ``siwe`` library for canonical parsing/verification. The library
takes care of EIP-191 hashing and signature recovery; we add nonce binding
and address normalisation around it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SiweVerification:
    ok: bool
    address: str | None
    reason: str | None = None


def verify_siwe(message: str, signature: str, expected_nonce: str | None = None) -> SiweVerification:
    """Verify a SIWE message + signature.

    Returns a ``SiweVerification`` rather than raising; the caller decides
    whether a failed verification is a 401, a 422, or something else.
    """
    try:
        from siwe import SiweMessage  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover
        return SiweVerification(False, None, "siwe package unavailable")

    try:
        msg = SiweMessage(message=message)
    except Exception as e:
        return SiweVerification(False, None, f"unparseable SIWE message: {e}")

    if expected_nonce and msg.nonce != expected_nonce:
        return SiweVerification(False, None, "nonce mismatch")

    try:
        msg.verify(signature)
    except Exception as e:
        return SiweVerification(False, None, f"signature verify failed: {e}")

    return SiweVerification(True, msg.address.lower(), None)
