"""Built-in jobs Chronos can schedule.

Each job is an async function with no arguments. They reach into the
rest of the Pantheon stack via Redis Streams and HTTP — there is no
direct Python import from the consumer-side services so Chronos stays
deployable independently.
"""

from __future__ import annotations

import json
import os

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger("chronos.jobs")

POLYMARKET_URL = os.environ.get(
    "POLYMARKET_CLOB_URL", "https://clob.polymarket.com/markets"
)
APOLLO_TRIGGER_KEY = "chronos:trigger:apollo"
BOULE_TRIGGER_KEY = "chronos:trigger:boule"
ANCHOR_RETRY_KEY = "chronos:trigger:anchor_retry"


async def _redis() -> aioredis.Redis:
    return await aioredis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )


async def apollo_scan() -> None:
    """Fire the Apollo prefilter against the Polymarket CLOB.

    Strategy: push a job message onto a Redis list that an Apollo
    worker consumes. We deliberately do NOT call Apollo in-process so
    Chronos remains a thin scheduler — the heavy lifting lives where
    it belongs.

    Polymarket reachability is best-effort: if the CLOB is geo-blocked
    or rate-limiting, we still publish the trigger so Apollo can
    decide how to react (e.g. fall back to cached signals).
    """
    log.info("chronos.apollo_scan.start")
    redis = await _redis()
    try:
        await redis.xadd(
            APOLLO_TRIGGER_KEY,
            {"data": json.dumps({"source": "chronos", "url": POLYMARKET_URL})},
            maxlen=1000,
            approximate=True,
        )
    finally:
        await redis.aclose()
    log.info("chronos.apollo_scan.done")


async def boule_sweep() -> None:
    """Trigger Boule consumer sweep — re-check stale theses and orphan traces."""
    log.info("chronos.boule_sweep.start")
    redis = await _redis()
    try:
        await redis.xadd(
            BOULE_TRIGGER_KEY,
            {"data": json.dumps({"source": "chronos", "kind": "sweep"})},
            maxlen=1000,
            approximate=True,
        )
    finally:
        await redis.aclose()
    log.info("chronos.boule_sweep.done")


async def restraint_anchor_retry() -> None:
    """Tell Areopagus to retry on-chain anchors for proofs missing a tx hash.

    The chain writer is best-effort and fire-and-forget; transient RPC
    failures silently drop the on-chain write while Redis keeps the
    canonical record. This job re-emits unanchored proof_ids so the
    consumer can re-fire ``ProofOfRestraint.declineTrade``.
    """
    log.info("chronos.anchor_retry.start")
    redis = await _redis()
    try:
        await redis.xadd(
            ANCHOR_RETRY_KEY,
            {"data": json.dumps({"source": "chronos", "kind": "anchor_retry"})},
            maxlen=1000,
            approximate=True,
        )
    finally:
        await redis.aclose()
    log.info("chronos.anchor_retry.done")
