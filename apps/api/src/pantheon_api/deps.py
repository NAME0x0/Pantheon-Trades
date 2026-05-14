"""Shared FastAPI dependencies — DB session, Redis client, current user."""

from __future__ import annotations

import os
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pantheon_api.auth.session import SessionPayload, decode_session
from pantheon_api.config import settings
from pantheon_api.db import get_session

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> SessionPayload:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization.split(None, 1)[1].strip()
    payload = decode_session(token, secret=settings.secret_key)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return payload


def require_role(*allowed: str):
    async def _check(user: Annotated[SessionPayload, Depends(current_user)]) -> SessionPayload:
        if not any(role in allowed for role in user.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role not permitted")
        return user
    return _check


SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]
UserDep = Annotated[SessionPayload, Depends(current_user)]
