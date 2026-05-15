"""Boule consumer — reads Apollo signals, runs deliberation, publishes theses.

The consumer is the production glue Boule's services-mode entrypoint runs.
It reads from the ``apollo:signals`` Redis stream with a consumer group so
multiple Boule replicas can share work without double-processing a signal,
runs the full council debate, publishes the resulting Thesis to the
``boule:theses`` stream, and hands the bundle to Parthenon for IPFS pinning
and on-chain Merkle anchoring.

Idempotency rules:
- A signal is processed at most once per consumer group (XREADGROUP +
  XACK).
- If deliberation crashes, we leave the message unacknowledged so a sibling
  worker can retry once the pending entry list times out.
- The thesis_id is uuid'd inside ``swarm.deliberate`` so even a retry
  emits a fresh thesis row (Parthenon archive de-duplicates on manifest
  CID downstream).
"""

from __future__ import annotations

import json
import os
from typing import Any

import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import Signal, Thesis

from boule.healing.circuit_breaker import CircuitBreaker
from boule.healing.schema_repair import repair_and_validate
from boule.llm import LLMClient, build_default_client
from boule.swarm import deliberate

log = structlog.get_logger("boule.consumer")

APOLLO_STREAM = "apollo:signals"
THESES_STREAM = "boule:theses"
CONSUMER_GROUP = "boule"
DEFAULT_CONSUMER_NAME = os.environ.get("HOSTNAME", "boule-1")
BLOCK_MS = 5_000
BATCH = 5
PENDING_MIN_IDLE_MS = 60_000


async def _ensure_group(redis: aioredis.Redis) -> None:
    try:
        await redis.xgroup_create(
            name=APOLLO_STREAM, groupname=CONSUMER_GROUP, id="$", mkstream=True
        )
        log.info("boule.consumer.group_created", group=CONSUMER_GROUP)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _publish_thesis(redis: aioredis.Redis, thesis: Thesis) -> None:
    await redis.xadd(
        THESES_STREAM,
        {"data": thesis.model_dump_json()},
        maxlen=50_000,
        approximate=True,
    )
    await redis.setex(
        f"boule:thesis:{thesis.thesis_id}",
        86_400,
        thesis.model_dump_json(),
    )


async def _maybe_archive(thesis: Thesis, signal: Signal) -> None:
    """Hand the thesis bundle to Parthenon for IPFS + on-chain anchoring.

    Imported lazily so Boule does not pull web3 + IPFS deps into the hot
    path of every deliberation — only the consumer reaches for them.
    """
    if os.environ.get("PARTHENON_ARCHIVE_ENABLED", "1") not in ("1", "true", "yes"):
        return
    try:
        from parthenon.archive import Archive
        from parthenon.ipfs import IpfsClient
    except ImportError as e:
        log.warning("boule.consumer.parthenon_unavailable", error=str(e))
        return

    ipfs = IpfsClient.from_env()
    archive = Archive(ipfs=ipfs)
    try:
        result = await archive.archive_thesis_bundle(
            signal=signal,
            thesis=thesis,
            trace=[],  # tracer events stream separately; consumer can join later
        )
        thesis.archived_cid = result.manifest_cid
        log.info(
            "boule.consumer.archived",
            thesis_id=thesis.thesis_id,
            manifest_cid=result.manifest_cid,
            merkle_root=result.merkle_root,
        )
        # On-chain anchor is best-effort — failures are logged but never block.
        if os.environ.get("PARTHENON_REGISTRY_ADDRESS"):
            try:
                from parthenon.anchor import AnchorService

                receipt = await AnchorService().anchor(
                    manifest_cid=result.manifest_cid,
                    merkle_root=result.merkle_root,
                    kind="thesis",
                )
                log.info(
                    "boule.consumer.anchored",
                    thesis_id=thesis.thesis_id,
                    tx_hash=receipt.tx_hash,
                    block=receipt.block_number,
                )
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "boule.consumer.anchor_failed",
                    thesis_id=thesis.thesis_id,
                    error=str(e),
                )
    except Exception as e:  # noqa: BLE001
        log.warning("boule.consumer.archive_failed", error=str(e))
    finally:
        await ipfs.close()


async def _process_one(
    redis: aioredis.Redis,
    llm_client: LLMClient,
    raw_signal: dict[str, Any],
    breaker: CircuitBreaker,
) -> Thesis | None:
    # First try strict validation; fall back to tolerant repair before giving up.
    try:
        signal = Signal.model_validate(raw_signal)
    except Exception:
        signal = repair_and_validate(Signal, json.dumps(raw_signal))
        if signal is None:
            log.warning("boule.consumer.unrepairable_signal")
            return None
        log.info("boule.consumer.signal_repaired", signal_id=signal.signal_id)

    if not breaker.allow():
        log.warning(
            "boule.consumer.breaker_open",
            state=breaker.state.value,
            failures=breaker.failures,
        )
        return None

    log.info(
        "boule.consumer.deliberating",
        signal_id=signal.signal_id,
        market=signal.market_id,
        band=signal.band,
    )
    try:
        thesis = await deliberate(
            signal,
            llm_client=llm_client,
            redis_client=redis,
        )
    except Exception:
        breaker.record_failure()
        raise
    breaker.record_success()
    await _publish_thesis(redis, thesis)
    await _maybe_archive(thesis, signal)
    return thesis


async def consume_forever(
    redis_url: str | None = None,
    consumer_name: str = DEFAULT_CONSUMER_NAME,
) -> None:
    redis = await aioredis.from_url(
        redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    llm_client = build_default_client()
    breaker = CircuitBreaker(name="boule.deliberate", failure_threshold=5, reset_timeout_seconds=60.0)

    await _ensure_group(redis)
    log.info("boule.consumer.start", consumer=consumer_name)

    try:
        while True:
            response = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={APOLLO_STREAM: ">"},
                count=BATCH,
                block=BLOCK_MS,
            )
            if not response:
                continue
            for _stream, entries in response:
                for entry_id, fields in entries:
                    payload = fields.get("data") if isinstance(fields, dict) else None
                    if not payload:
                        await redis.xack(APOLLO_STREAM, CONSUMER_GROUP, entry_id)
                        continue
                    try:
                        raw_signal = json.loads(payload)
                    except (ValueError, json.JSONDecodeError):
                        log.warning("boule.consumer.bad_payload", entry_id=entry_id)
                        await redis.xack(APOLLO_STREAM, CONSUMER_GROUP, entry_id)
                        continue
                    try:
                        await _process_one(redis, llm_client, raw_signal, breaker)
                    except Exception as e:  # noqa: BLE001
                        log.exception(
                            "boule.consumer.process_failed",
                            entry_id=entry_id,
                            error=str(e),
                        )
                        # Leave unacked; PEL retry picks it up.
                        continue
                    await redis.xack(APOLLO_STREAM, CONSUMER_GROUP, entry_id)
    finally:
        await redis.aclose()
        await llm_client.close()
