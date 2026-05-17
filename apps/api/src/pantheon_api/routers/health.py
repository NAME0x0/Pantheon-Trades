"""Health and liveness endpoints.

Two layers:

  /health      cheap liveness — Redis ping + DB SELECT 1. Returns
               degraded on any failure but does not probe deeper
               systems (RPC, IPFS) so it stays fast and the load
               balancer can poll it aggressively.

  /health/deep deep readiness — Redis info, DB version, RPC chainId,
               IPFS id(). Each probe is bounded by a per-probe
               timeout so a slow upstream never blocks the response
               beyond ``TOTAL_BUDGET_S``. Use for oncall dashboards
               and pre-deploy gating, NOT load-balancer health checks.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx
import structlog
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from pantheon_api.deps import RedisDep, SessionDep

log = structlog.get_logger("pantheon_api.health")
router = APIRouter(tags=["health"])

PROBE_TIMEOUT_S = float(os.environ.get("HEALTH_PROBE_TIMEOUT_S", "2"))
TOTAL_BUDGET_S = float(os.environ.get("HEALTH_TOTAL_BUDGET_S", "5"))


class HealthResponse(BaseModel):
    status: str
    version: str
    redis: str
    db: str


class ProbeResult(BaseModel):
    ok: bool
    latency_ms: int
    detail: str = ""


class DeepHealthResponse(BaseModel):
    status: str
    redis: ProbeResult
    db: ProbeResult
    rpc: ProbeResult
    ipfs: ProbeResult


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


@router.get("/health/deep", response_model=DeepHealthResponse)
async def deep_health(db: SessionDep, redis: RedisDep) -> DeepHealthResponse:
    """Run every probe under a total time budget; each probe is also
    bounded individually so a single hanging upstream cannot poison
    the response."""
    started = time.monotonic()

    async def _budget_left() -> float:
        used = time.monotonic() - started
        return max(0.5, TOTAL_BUDGET_S - used)

    redis_p = await _probe(_probe_redis(redis), per=PROBE_TIMEOUT_S)
    db_p = await _probe(_probe_db(db), per=PROBE_TIMEOUT_S)
    rpc_p = await _probe(_probe_rpc(), per=min(PROBE_TIMEOUT_S, await _budget_left()))
    ipfs_p = await _probe(_probe_ipfs(), per=min(PROBE_TIMEOUT_S, await _budget_left()))

    overall = "ok" if all(p.ok for p in (redis_p, db_p)) else "degraded"
    # RPC/IPFS missing-config is "skipped", not failure — only the
    # core stores need to be green for the API itself.
    return DeepHealthResponse(status=overall, redis=redis_p, db=db_p, rpc=rpc_p, ipfs=ipfs_p)


@router.get("/")
async def root() -> dict:
    return {"service": "pantheon-api", "docs": "/docs"}


# ─── probe helpers ──


async def _probe(coro, *, per: float) -> ProbeResult:
    t0 = time.monotonic()
    try:
        detail = await asyncio.wait_for(coro, timeout=per)
        return ProbeResult(ok=True, latency_ms=int((time.monotonic() - t0) * 1000), detail=detail or "")
    except asyncio.TimeoutError:
        return ProbeResult(ok=False, latency_ms=int(per * 1000), detail=f"timeout > {per:.1f}s")
    except Exception as e:  # noqa: BLE001
        return ProbeResult(ok=False, latency_ms=int((time.monotonic() - t0) * 1000), detail=str(e)[:200])


async def _probe_redis(redis) -> str:
    info = await redis.info(section="server")
    version = info.get("redis_version", "?") if isinstance(info, dict) else "?"
    return f"redis {version}"


async def _probe_db(db) -> str:
    row = (await db.execute(text("SELECT version()"))).scalar_one()
    return str(row)[:80]


async def _probe_rpc() -> str:
    url = os.environ.get("RPC_URL")
    if not url:
        return "RPC_URL not set"
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as http:
        resp = await http.post(
            url,
            json={"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        return f"chainId={data.get('result', '?')}"


async def _probe_ipfs() -> str:
    url = os.environ.get("IPFS_API_URL")
    if not url:
        return "IPFS_API_URL not set"
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as http:
        resp = await http.post(f"{url.rstrip('/')}/api/v0/id")
        resp.raise_for_status()
        return resp.json().get("ID", "?")[:40]
