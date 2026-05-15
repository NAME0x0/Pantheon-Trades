"""Auth router — SIWE nonce/verify flow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from pantheon_api.auth.allowlist import roles_for
from pantheon_api.auth.nonce import consume_nonce, issue_nonce
from pantheon_api.auth.session import SessionPayload, issue_session
from pantheon_api.auth.siwe import verify_siwe
from pantheon_api.config import settings
from pantheon_api.deps import RedisDep, UserDep

router = APIRouter()


class NonceResponse(BaseModel):
    address: str
    nonce: str


class VerifyRequest(BaseModel):
    message: str = Field(..., description="The full SIWE message that was signed.")
    signature: str = Field(..., description="0x-prefixed signature.")


class VerifyResponse(BaseModel):
    address: str
    roles: list[str]
    token: str


class MeResponse(BaseModel):
    address: str
    roles: list[str]


@router.get("/nonce", response_model=NonceResponse)
async def nonce(address: str, redis: RedisDep) -> NonceResponse:
    addr = address.lower().strip()
    if not addr.startswith("0x") or len(addr) != 42:
        raise HTTPException(status_code=400, detail="invalid address")
    n = await issue_nonce(redis, addr)
    return NonceResponse(address=addr, nonce=n)


@router.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest, redis: RedisDep) -> VerifyResponse:
    verification = verify_siwe(req.message, req.signature)
    if not verification.ok or verification.address is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=verification.reason or "siwe verification failed")
    address = verification.address
    # Extract nonce from the SIWE message; verify_siwe already validated it
    # against the signature, we just need to consume it from Redis.
    nonce_line = next((line for line in req.message.splitlines() if line.lower().startswith("nonce:")), None)
    siwe_nonce = nonce_line.split(":", 1)[1].strip() if nonce_line else ""
    if not await consume_nonce(redis, address, siwe_nonce):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="nonce not found or already used")
    roles = roles_for(address)
    payload = SessionPayload(address=address, roles=roles)
    token = issue_session(payload, secret=settings.secret_key)
    return VerifyResponse(address=address, roles=roles, token=token)


@router.get("/me", response_model=MeResponse)
async def me(user: UserDep) -> MeResponse:
    return MeResponse(address=user.address, roles=user.roles)
