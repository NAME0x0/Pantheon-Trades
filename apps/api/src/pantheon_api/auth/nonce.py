"""SIWE nonce store backed by Redis.

A nonce is issued per ``/auth/nonce`` request, scoped to the requesting
address, and consumed (one-shot) when the signed SIWE message is verified.
Nonces expire after ``NONCE_TTL_SECONDS`` even if unused.
"""

from __future__ import annotations

import secrets

import redis.asyncio as aioredis


NONCE_TTL_SECONDS = 600  # 10 minutes
NONCE_PREFIX = "auth:nonce"


def _key(address: str, nonce: str) -> str:
    return f"{NONCE_PREFIX}:{address.lower()}:{nonce}"


def generate_nonce() -> str:
    return secrets.token_urlsafe(16)


async def issue_nonce(redis: aioredis.Redis, address: str) -> str:
    nonce = generate_nonce()
    await redis.setex(_key(address, nonce), NONCE_TTL_SECONDS, "1")
    return nonce


async def consume_nonce(redis: aioredis.Redis, address: str, nonce: str) -> bool:
    """One-shot — returns True iff the nonce existed and is now deleted."""
    deleted = await redis.delete(_key(address, nonce))
    return bool(deleted)
