"""Health and liveness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from pantheon_api.deps import RedisDep, SessionDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    redis: str
    db: str


@router.get("/health", response_model=HealthResponse)
async def health(db: SessionDep, redis: RedisDep) -> HealthResponse:
    redis_status = "down"
    try:
        if await redis.ping():
            redis_status = "ok"
    except Exception:
        redis_status = "down"

    db_status = "down"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "down"

    overall = "ok" if redis_status == "ok" and db_status == "ok" else "degraded"
    return HealthResponse(status=overall, version="0.1.0", redis=redis_status, db=db_status)


@router.get("/")
async def root() -> dict:
    return {"service": "pantheon-api", "docs": "/docs"}
