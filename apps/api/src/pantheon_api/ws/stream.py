"""WebSocket stream — multiplexes Redis streams to dashboard clients.

Each client opens ``GET /ws?streams=boule:traces,strategos:trades`` and
receives newline-delimited JSON events as they arrive. Heartbeats are
sent every 30s so intermediate proxies do not idle-close the socket.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

log = structlog.get_logger("pantheon_api.ws")

router = APIRouter()

DEFAULT_STREAMS = (
    "apollo:signals",
    "boule:traces",
    "boule:theses",
    "areopagus:approvals",
    "areopagus:rejections",
    "strategos:trades",
    "argos:exits",
)
HEARTBEAT_INTERVAL = 30.0


@router.websocket("/ws")
async def stream(
    websocket: WebSocket,
    streams: str = Query(default=",".join(DEFAULT_STREAMS)),
) -> None:
    await websocket.accept()
    selected = [s.strip() for s in streams.split(",") if s.strip()]
    if not selected:
        await websocket.close(code=4000)
        return

    redis = await aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    cursors: dict[str, str] = {s: "$" for s in selected}
    log.info("ws.stream.start", streams=selected)

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            try:
                await websocket.send_json({"event": "ping"})
            except Exception:
                return

    hb_task = asyncio.create_task(heartbeat())
    try:
        while True:
            try:
                response = await redis.xread(streams=cursors, block=5_000, count=20)
            except Exception as e:  # noqa: BLE001
                log.warning("ws.stream.redis_failed", error=str(e))
                await asyncio.sleep(1.0)
                continue
            if not response:
                continue
            for stream_name, entries in response:
                for entry_id, fields in entries:
                    cursors[stream_name] = entry_id
                    payload: Any = None
                    if isinstance(fields, dict) and "data" in fields:
                        try:
                            payload = json.loads(fields["data"])
                        except (ValueError, json.JSONDecodeError):
                            payload = fields["data"]
                    await websocket.send_json(
                        {"stream": stream_name, "id": entry_id, "data": payload}
                    )
    except WebSocketDisconnect:
        log.info("ws.stream.disconnect")
    finally:
        hb_task.cancel()
        await redis.aclose()
