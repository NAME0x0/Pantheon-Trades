"""Base class for every Boule council agent.

Each agent is a Claude API client with three mandatory phases — opening
(Round 1), challenge (Round 2), vote (Round 4) — plus an optional synthesis
hook used only by Athena. The base handles tracing, retry/backoff, and the
shared signal-context formatter so each subclass stays small.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod

import anthropic
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from pantheon_core.schema import Signal, ThesisBlock

from boule.trace import Tracer

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
CALL_TIMEOUT_SECONDS = 45.0
MAX_RETRIES = 3

log = structlog.get_logger("boule.agent")

_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class CouncilAgent(ABC):
    """ABC for every agent in the deliberation council."""

    name: str
    weight: float = 1.0
    has_veto: bool = False

    def __init__(self, client: anthropic.AsyncAnthropic, tracer: Tracer, prompt: str) -> None:
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
        response = await self._anthropic_call(messages)
        latency_ms = int((time.monotonic() - t0) * 1000)

        content = _extract_text(response)
        usage = getattr(response, "usage", None)
        tokens = 0
        if usage is not None:
            tokens = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "output_tokens", 0) or 0)

        block = ThesisBlock(
            agent=self.name,
            round=round_num,
            content=content,
            tokens=tokens,
            latency_ms=latency_ms,
        )
        await self._tracer.emit(
            "agent_output",
            content,
            agent=self.name,
            round=round_num,
            tokens=tokens,
            latency_ms=latency_ms,
        )
        return block

    async def _anthropic_call(self, messages: list[dict]):
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(MAX_RETRIES),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=True,
        ):
            with attempt:
                return await asyncio.wait_for(
                    self._client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        system=self._system_prompt,
                        messages=messages,
                    ),
                    timeout=CALL_TIMEOUT_SECONDS,
                )

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


def _extract_text(response) -> str:
    """Pull the assistant text block out of an Anthropic response.

    Handles tool_use and other block types by concatenating any text blocks
    in order. Returns empty string if the response had no text.
    """
    chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            chunks.append(getattr(block, "text", "") or "")
        elif block_type is None and hasattr(block, "text"):
            chunks.append(block.text or "")
    return "\n".join(chunks).strip()
