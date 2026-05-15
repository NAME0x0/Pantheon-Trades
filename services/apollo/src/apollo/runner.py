"""Apollo runner — periodic scan that turns market snapshots into Signals.

The runner is intentionally framework-light: ``ApolloRunner.scan_once`` is
fully pure given an iterable of ``MarketSnapshot`` records, which makes it
trivial to test. ``run_forever`` wires up a Redis client and a snapshot
source. Production deployments inject a Pythia client; tests pass a fake.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import structlog
from redis.asyncio import Redis

from pantheon_core.schema import Signal

from apollo.bands import ELIGIBLE_BANDS
from apollo.filters import prefilter
from apollo.scorer import MarketSnapshot, score_market

log = structlog.get_logger("apollo.runner")

SIGNAL_STREAM = "apollo:signals"
DEFAULT_STREAM_MAXLEN = 50_000

SnapshotSource = Callable[[], Awaitable[list[MarketSnapshot]]]


class ApolloRunner:
    """Pulls snapshots, scores them, publishes S/A signals to Redis."""

    def __init__(
        self,
        source: SnapshotSource,
        redis: Redis,
        stream: str = SIGNAL_STREAM,
        stream_maxlen: int = DEFAULT_STREAM_MAXLEN,
        eligible_bands: set[str] = ELIGIBLE_BANDS,
    ) -> None:
        self._source = source
        self._redis = redis
        self._stream = stream
        self._maxlen = stream_maxlen
        self._eligible_bands = eligible_bands

    async def scan_once(self) -> list[Signal]:
        snapshots = await self._source()
        out: list[Signal] = []
        rejected = 0
        for snap in snapshots:
            verdict = prefilter(snap)
            if not verdict.passed:
                rejected += 1
                log.debug("apollo.prefilter_drop", market=snap.market_id, reason=verdict.reason)
                continue
            sig = score_market(snap)
            if sig.band in self._eligible_bands:
                out.append(sig)
        log.info(
            "apollo.scan",
            scanned=len(snapshots),
            published=len(out),
            prefiltered=rejected,
        )
        return out

    async def publish(self, signal: Signal) -> None:
        try:
            await self._redis.xadd(
                self._stream,
                {"data": signal.model_dump_json()},
                maxlen=self._maxlen,
                approximate=True,
            )
        except Exception as e:
            log.warning("apollo.publish_failed", signal_id=signal.signal_id, error=str(e))

    async def run_forever(self, interval_seconds: float = 30.0) -> None:
        while True:
            try:
                signals = await self.scan_once()
                for sig in signals:
                    await self.publish(sig)
            except Exception as e:
                log.exception("apollo.scan_failed", error=str(e))
            await asyncio.sleep(interval_seconds)
