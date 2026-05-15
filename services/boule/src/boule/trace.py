from __future__ import annotations


import redis.asyncio as aioredis
import structlog

from pantheon_core.schema import TraceEvent, utc_now

log = structlog.get_logger("boule.trace")


class Tracer:
    """Emits TraceEvents to a Redis stream and keeps an in-memory replay buffer.

    Each event is published exactly once, with monotonically increasing
    sequence numbers so consumers can detect gaps. Redis publish errors are
    logged but never raised — losing a trace event must never crash the
    deliberation. Parthenon is the source of truth for permanent archival.
    """

    STREAM_KEY = "boule:traces"
    MAX_STREAM_LEN = 100_000

    def __init__(
        self,
        redis_client: aioredis.Redis,
        trace_id: str,
        thesis_id: str,
        signal_id: str,
        market_id: str,
    ) -> None:
        self._redis = redis_client
        self.trace_id = trace_id
        self.thesis_id = thesis_id
        self.signal_id = signal_id
        self.market_id = market_id
        self._seq = 0
        self._events: list[TraceEvent] = []

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    async def emit(
        self,
        event_type: str,
        content: str,
        *,
        agent: str | None = None,
        round: int | None = None,
        tokens: int | None = None,
        latency_ms: int | None = None,
        vote: str | None = None,
        confidence: float | None = None,
        probability_estimate: float | None = None,
        flags: list[str] | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            trace_id=self.trace_id,
            thesis_id=self.thesis_id,
            signal_id=self.signal_id,
            market_id=self.market_id,
            event_type=event_type,  # type: ignore[arg-type]
            agent=agent,
            round=round,
            content=content,
            tokens=tokens,
            latency_ms=latency_ms,
            vote=vote,  # type: ignore[arg-type]
            confidence=confidence,
            probability_estimate=probability_estimate,
            flags=flags or [],
            timestamp=utc_now(),
            sequence=self._next_seq(),
        )
        self._events.append(event)
        try:
            await self._redis.xadd(
                self.STREAM_KEY,
                {"data": event.model_dump_json()},
                maxlen=self.MAX_STREAM_LEN,
                approximate=True,
            )
        except Exception as e:
            log.warning(
                "trace.emit.redis_failed",
                event_type=event_type,
                trace_id=self.trace_id,
                error=str(e),
            )
        return event

    @property
    def events(self) -> list[TraceEvent]:
        return list(self._events)
