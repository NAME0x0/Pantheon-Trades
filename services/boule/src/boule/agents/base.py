"""Base class for every Boule council agent.

Each agent runs three mandatory phases — opening (Round 1), challenge
(Round 2), vote (Round 4) — plus an optional synthesis hook used only by
Athena. The base handles tracing and the shared signal-context
formatter. Provider-specific retry / timeout / circuit-breaker logic
lives inside :mod:`boule.llm` so this class stays provider-agnostic.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import structlog

from pantheon_core.schema import Signal, ThesisBlock

from boule.llm import LLMClient
from boule.telemetry import CostRow, ledger, record_fingerprint
from boule.trace import Tracer

MAX_TOKENS = 1024

log = structlog.get_logger("boule.agent")


class CouncilAgent(ABC):
    """ABC for every agent in the deliberation council."""

    name: str
    weight: float = 1.0
    has_veto: bool = False

    def __init__(self, client: LLMClient, tracer: Tracer, prompt: str) -> None:
        self._client = client
        self._tracer = tracer
        self._system_prompt = prompt

    @abstractmethod
    async def opening(self, signal: Signal) -> ThesisBlock:
        """Round 1 — initial assessment."""

    @abstractmethod
    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        """Round 2 — challenge other agents' claims."""

    @abstractmethod
    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        """Round 4 — return (vote, confidence, probability_estimate, flags)."""

    async def _call(self, messages: list[dict], round_num: int) -> ThesisBlock:
        t0 = time.monotonic()
        result = await self._client.complete(
            system=self._system_prompt,
            messages=messages,
            max_tokens=MAX_TOKENS,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        block = ThesisBlock(
            agent=self.name,
            round=round_num,
            content=result.text,
            tokens=result.tokens,
            latency_ms=latency_ms,
        )
        # ── Telemetry: model drift + per-thesis cost attribution ─────
        # Best-effort. Telemetry errors must never crash the agent.
        try:
            drift_event = record_fingerprint(result.model_fingerprint)
            if drift_event:
                await self._tracer.emit(
                    "model_drift",
                    f"calibration may be stale: {drift_event}",
                    agent=self.name,
                    round=round_num,
                    flags=["model_drift"],
                )
            # Token split fallback if the adapter only returned a total.
            tokens_in = result.tokens_in or int(result.tokens * 0.6)
            tokens_out = result.tokens_out or (result.tokens - tokens_in)
            model_label = result.model_fingerprint or getattr(self._client, "model", "")
            usd = ledger.estimate_usd(model_label, tokens_in, tokens_out)
            await ledger.record(
                CostRow(
                    thesis_id=self._tracer.thesis_id,
                    signal_id=self._tracer.signal_id,
                    agent=self.name,
                    round=round_num,
                    provider=model_label.split("/", 1)[0] if "/" in model_label else "",
                    model=model_label,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    usd=usd,
                    timestamp=time.time(),
                )
            )
        except Exception as e:  # noqa: BLE001
            log.warning("boule.telemetry_failed", error=str(e))

        await self._tracer.emit(
            "agent_output",
            result.text,
            agent=self.name,
            round=round_num,
            tokens=result.tokens,
            latency_ms=latency_ms,
        )
        return block

    def _signal_context(self, signal: Signal) -> str:
        days = signal.days_to_resolution
        days_s = f"{days:.1f}" if days is not None else "n/a"
        return (
            f"Market: {signal.question}\n"
            f"Market ID: {signal.market_id}\n"
            f"Category: {signal.category}\n"
            f"Market probability (YES): {signal.market_probability:.2%}\n"
            f"Oracle probability (YES): {signal.oracle_probability:.2%}\n"
            f"Edge (signed, oracle - market): {signal.edge:+.2%}\n"
            f"|Edge|: {signal.edge_abs:.2%}\n"
            f"Band: {signal.band} (score: {signal.band_score:.3f})\n"
            f"Liquidity: {signal.liquidity_score:.3f} | Volatility: {signal.volatility_score:.3f}\n"
            f"Catalyst: {signal.catalyst_score:.3f} | Sentiment: {signal.sentiment_score:.3f}\n"
            f"Trend: {signal.trend_score:.3f} | Correlation: {signal.correlation_score:.3f}\n"
            f"Volume 24h: ${signal.volume_24h:,.0f} USDC\n"
            f"Open interest: ${signal.open_interest:,.0f} USDC\n"
            f"Best bid/ask: {signal.bid:.3f} / {signal.ask:.3f} (spread {signal.spread:.2%})\n"
            f"Days to resolution: {days_s}\n"
            f"Data staleness: {signal.staleness_seconds}s | Source trust: {signal.source_trust_score:.3f}\n"
            f"Sources: {', '.join(signal.data_sources)}"
        )
