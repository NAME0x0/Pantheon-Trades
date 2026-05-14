"""Aggregate service health derived from Redis heartbeats."""

from __future__ import annotations

from dataclasses import dataclass

import redis.asyncio as aioredis


HEARTBEAT_KEYS = (
    "argos:heartbeat",
    "olympus:state",
    "ostrakon:weights:zeus",  # any agent score key proves Ostrakon ran
)


@dataclass(frozen=True)
class ServiceHealthReport:
    name: str
    healthy: bool
    note: str = ""


async def service_health(redis: aioredis.Redis) -> list[ServiceHealthReport]:
    reports: list[ServiceHealthReport] = []
    for key in HEARTBEAT_KEYS:
        try:
            raw = await redis.get(key)
        except Exception as e:  # noqa: BLE001
            reports.append(ServiceHealthReport(name=key, healthy=False, note=str(e)))
            continue
        reports.append(ServiceHealthReport(name=key, healthy=raw is not None))
    return reports


async def summary(redis: aioredis.Redis) -> dict:
    reports = await service_health(redis)
    healthy = sum(1 for r in reports if r.healthy)
    return {
        "healthy": healthy,
        "total": len(reports),
        "reports": [{"name": r.name, "healthy": r.healthy, "note": r.note} for r in reports],
    }
