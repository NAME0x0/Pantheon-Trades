"""Areopagus consumer — gates theses post-deliberation.

Reads ``boule:theses`` via a consumer group, runs
``AreopagusCourt.evaluate_thesis``, publishes either an ApprovalToken on
``areopagus:approvals`` (Strategos picks these up) or a RejectionRecord on
``areopagus:rejections`` plus a ProofOfRestraint when the signal cleared
the pre-gates but the thesis failed.

The signal payload accompanying each thesis is required for portfolio /
category exposure checks; we look it up from Redis where Boule cached it
(``boule:signal:<signal_id>``). If missing, the gate runs against a
zero-exposure portfolio and a synthetic empty signal — which is the safe
default since gates only loosen exposure.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import ApprovalToken, RejectionRecord, Signal, Thesis

from areopagus.chain import RestraintChainWriter
from areopagus.court import AreopagusCourt
from areopagus.gates import PortfolioState

log = structlog.get_logger("areopagus.consumer")

THESES_STREAM = "boule:theses"
APPROVALS_STREAM = "areopagus:approvals"
REJECTIONS_STREAM = "areopagus:rejections"
RESTRAINT_STREAM = "areopagus:restraint"
CONSUMER_GROUP = "areopagus"
DEFAULT_CONSUMER_NAME = os.environ.get("HOSTNAME", "areopagus-1")
BLOCK_MS = 5_000
BATCH = 10


async def _ensure_group(redis: aioredis.Redis) -> None:
    try:
        await redis.xgroup_create(
            name=THESES_STREAM, groupname=CONSUMER_GROUP, id="$", mkstream=True
        )
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _fetch_signal(redis: aioredis.Redis, signal_id: str) -> Signal | None:
    raw = await redis.get(f"boule:signal:{signal_id}")
    if not raw:
        # Boule does not currently mirror signal payloads — fall back to the
        # Apollo stream cache.
        raw = await redis.get(f"apollo:signal:{signal_id}")
    if not raw:
        return None
    try:
        return Signal.model_validate_json(raw)
    except Exception as e:  # noqa: BLE001
        log.warning("areopagus.consumer.bad_signal_cache", error=str(e))
        return None


async def _fetch_portfolio(redis: aioredis.Redis) -> PortfolioState:
    raw = await redis.get("strategos:portfolio")
    if not raw:
        return PortfolioState()
    try:
        data = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return PortfolioState()
    return PortfolioState(
        open_positions=int(data.get("open_positions", 0)),
        total_exposure=float(data.get("total_exposure", 0.0)),
        category_exposure=data.get("category_exposure", {}) or {},
        drawdown_pause=bool(data.get("drawdown_pause", False)),
        daily_drawdown=float(data.get("daily_drawdown", 0.0)),
        weekly_drawdown=float(data.get("weekly_drawdown", 0.0)),
    )


async def _publish(redis: aioredis.Redis, stream: str, payload: str) -> None:
    await redis.xadd(stream, {"data": payload}, maxlen=50_000, approximate=True)


def _empty_signal_for_thesis(thesis: Thesis) -> Signal:
    """Fallback signal envelope when the cache lookup misses — only used
    for exposure/category checks. Probabilities echo the thesis's own view.
    """
    return Signal(
        signal_id=thesis.signal_id,
        market_id=thesis.market_id,
        question=thesis.question,
        category="other",
        market_probability=thesis.raw_market_probability,
        oracle_probability=thesis.council_probability,
        edge=thesis.edge,
        edge_abs=abs(thesis.edge),
        band="A",
        band_score=0.7,
        liquidity_score=0.8,
        volatility_score=0.5,
        catalyst_score=0.5,
        sentiment_score=0.5,
        correlation_score=0.5,
        trend_score=0.5,
        volume_24h=0.0,
        open_interest=0.0,
        bid=0.0,
        ask=1.0,
        spread=0.0,
        data_sources=["thesis_fallback"],
        staleness_seconds=0,
        source_trust_score=0.5,
        pythia_snapshot_at=thesis.created_at,
    )


async def _anchor_and_update(
    redis: aioredis.Redis,
    chain_writer: RestraintChainWriter,
    proof_id: str,
    proof: Any,
) -> None:
    """Submit the on-chain witness and persist the tx hash under
    ``areopagus:restraint:tx:<proof_id>``.

    Runs as a background task so a slow RPC never blocks the consumer.
    """
    result = await chain_writer.write(proof)
    if result is None:
        return
    try:
        await redis.setex(
            f"areopagus:restraint:tx:{proof_id}",
            7 * 24 * 3600,
            json.dumps(
                {
                    "tx_hash": result.tx_hash,
                    "onchain_proof_id": result.proof_id,
                    "explorer_url": result.explorer_url,
                }
            ),
        )
    except Exception as e:  # noqa: BLE001
        log.warning("areopagus.chain.persist_failed", proof_id=proof_id, error=str(e))


async def _process(
    redis: aioredis.Redis,
    raw_thesis: dict[str, Any],
    chain_writer: RestraintChainWriter | None = None,
) -> None:
    try:
        thesis = Thesis.model_validate(raw_thesis)
    except Exception as e:  # noqa: BLE001
        log.warning("areopagus.consumer.bad_thesis", error=str(e))
        return

    signal = await _fetch_signal(redis, thesis.signal_id) or _empty_signal_for_thesis(thesis)
    portfolio = await _fetch_portfolio(redis)
    court = AreopagusCourt(portfolio=portfolio)

    verdict = court.evaluate_thesis(thesis, signal)
    if isinstance(verdict, ApprovalToken):
        await _publish(redis, APPROVALS_STREAM, verdict.model_dump_json())
        await redis.setex(
            f"areopagus:approval:{verdict.thesis_id}",
            86_400,
            verdict.model_dump_json(),
        )
        log.info(
            "areopagus.approved",
            thesis_id=thesis.thesis_id,
            decision=verdict.decision,
            size=verdict.final_size_pct,
        )
        return

    assert isinstance(verdict, RejectionRecord)
    await _publish(redis, REJECTIONS_STREAM, verdict.model_dump_json())

    # ProofOfRestraint when the signal cleared pre-gates but the thesis lost.
    try:
        proof = court.record_restraint(
            signal=signal,
            signal_json=signal.model_dump_json(),
            rejection=verdict,
        )
        await _publish(
            redis,
            RESTRAINT_STREAM,
            json.dumps(
                {
                    "proof_id": proof.proof_id,
                    "signal_id": proof.signal_id,
                    "market_id": proof.market_id,
                    "reason_code": proof.reason_code,
                    "note": proof.note,
                    "signal_hash": proof.signal_hash,
                    "created_at": proof.created_at.isoformat(),
                }
            ),
        )
        # Best-effort on-chain witness. Fire-and-forget so a slow / unreachable
        # RPC never blocks the consumer loop. Redis stream above remains
        # canonical; the chain write is a public audit trail, not the truth.
        # When the tx lands we update the Redis entry with the tx_hash so the
        # /restraint API surface can show an Arcscan link.
        if chain_writer is not None:
            asyncio.create_task(
                _anchor_and_update(redis, chain_writer, proof.proof_id, proof)
            )
    except Exception as e:  # noqa: BLE001
        log.warning("areopagus.restraint_failed", error=str(e))

    log.info(
        "areopagus.rejected",
        thesis_id=thesis.thesis_id,
        reason=verdict.reason_code,
    )


async def consume_forever(
    redis_url: str | None = None,
    consumer_name: str = DEFAULT_CONSUMER_NAME,
) -> None:
    redis = await aioredis.from_url(
        redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )
    await _ensure_group(redis)
    chain_writer = RestraintChainWriter.from_env()
    log.info(
        "areopagus.consumer.start",
        consumer=consumer_name,
        chain_writer_enabled=chain_writer is not None,
    )

    try:
        while True:
            response = await redis.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=consumer_name,
                streams={THESES_STREAM: ">"},
                count=BATCH,
                block=BLOCK_MS,
            )
            if not response:
                continue
            for _stream, entries in response:
                for entry_id, fields in entries:
                    payload = fields.get("data") if isinstance(fields, dict) else None
                    if not payload:
                        await redis.xack(THESES_STREAM, CONSUMER_GROUP, entry_id)
                        continue
                    try:
                        raw_thesis = json.loads(payload)
                    except (ValueError, json.JSONDecodeError):
                        await redis.xack(THESES_STREAM, CONSUMER_GROUP, entry_id)
                        continue
                    try:
                        await _process(redis, raw_thesis, chain_writer=chain_writer)
                    except Exception as e:  # noqa: BLE001
                        log.exception(
                            "areopagus.consumer.process_failed",
                            entry_id=entry_id,
                            error=str(e),
                        )
                        continue
                    await redis.xack(THESES_STREAM, CONSUMER_GROUP, entry_id)
    finally:
        if chain_writer is not None:
            await chain_writer.close()
        await redis.aclose()
