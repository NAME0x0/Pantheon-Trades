"""Tests for the Eris adversarial agent."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pantheon_core.schema import ThesisBlock

from boule.agents.adversarial import Eris, _infer_lean


class _StubLLM:
    """Minimal stub — records the last call and returns canned text."""

    def __init__(self, response: str) -> None:
        self.last_messages: list[dict] = []
        self._response = response
        self.model = "stub/stub-1"

    async def complete(self, *, system: str, messages: list[dict], max_tokens: int):
        self.last_messages = messages

        class R:
            text = self._response
            tokens = 100
            tokens_in = 60
            tokens_out = 40
            model_fingerprint = "stub/stub-1"

        return R()


class _StubTracer:
    thesis_id = "t1"
    signal_id = "s1"

    async def emit(self, *args, **kwargs):
        return None


def _block(agent: str, content: str, round_num: int = 1) -> ThesisBlock:
    return ThesisBlock(agent=agent, round=round_num, content=content, tokens=80, latency_ms=10)


def test_infer_lean_yes_when_approve_dominates():
    blocks = [
        _block("ares", "APPROVE — strong edge"),
        _block("athena", "Recommending BUY"),
        _block("hephaestus", "I would APPROVE"),
        _block("cassandra", "Mild concern but APPROVE"),
    ]
    assert _infer_lean(blocks) == "yes"


def test_infer_lean_no_when_reject_dominates():
    blocks = [
        _block("ares", "REJECT — weak case"),
        _block("athena", "SHORT this market"),
        _block("hephaestus", "I would REJECT"),
    ]
    assert _infer_lean(blocks) == "no"


def test_infer_lean_unclear_when_no_directional_tokens():
    blocks = [
        _block("ares", "this market is interesting"),
        _block("athena", "we should think more"),
    ]
    assert _infer_lean(blocks) == "unclear"


def test_infer_lean_empty_blocks():
    assert _infer_lean([]) == "unclear"


@pytest.mark.asyncio
async def test_eris_challenge_targets_minority_when_council_leans_yes():
    eris = Eris(client=_StubLLM("counter-case here"), tracer=_StubTracer(), prompt="eris persona")
    signal = _make_signal()
    blocks = [
        _block("ares", "APPROVE — bullish"),
        _block("athena", "I lean APPROVE"),
        _block("hephaestus", "BUY this"),
    ]
    block = await eris.challenge(signal, blocks)
    # The challenge prompt should mention NO / REJECT as the target.
    prompt_text = eris._client.last_messages[0]["content"]  # type: ignore[attr-defined]
    assert "NO / REJECT" in prompt_text
    assert block.agent == "eris"
    assert block.round == 2


@pytest.mark.asyncio
async def test_eris_challenge_targets_yes_when_council_leans_no():
    eris = Eris(client=_StubLLM("counter-case"), tracer=_StubTracer(), prompt="persona")
    blocks = [
        _block("zeus", "REJECT — violates risk policy"),
        _block("solon", "I would REJECT"),
    ]
    await eris.challenge(_make_signal(), blocks)
    prompt_text = eris._client.last_messages[0]["content"]  # type: ignore[attr-defined]
    assert "YES / APPROVE" in prompt_text


@pytest.mark.asyncio
async def test_eris_challenge_handles_unclear_lean():
    eris = Eris(client=_StubLLM("..."), tracer=_StubTracer(), prompt="persona")
    blocks = [_block("ares", "interesting market with novel structure")]
    await eris.challenge(_make_signal(), blocks)
    prompt_text = eris._client.last_messages[0]["content"]  # type: ignore[attr-defined]
    assert "overrepresented" in prompt_text


@pytest.mark.asyncio
async def test_eris_challenge_filters_to_round_1():
    eris = Eris(client=_StubLLM("..."), tracer=_StubTracer(), prompt="persona")
    mixed = [
        _block("ares", "APPROVE", round_num=1),
        _block("ares", "i changed my mind, REJECT", round_num=2),
        _block("eris", "previous eris block", round_num=1),  # should be filtered out
    ]
    await eris.challenge(_make_signal(), mixed)
    prompt_text = eris._client.last_messages[0]["content"]  # type: ignore[attr-defined]
    # Round-2 reject and our own block should not appear in the transcript.
    assert "i changed my mind" not in prompt_text
    assert "previous eris" not in prompt_text


# ───────────────────────── helpers ─────────────────────────


def _make_signal():
    from pantheon_core.schema import Signal

    return Signal(
        market_id="0xabc",
        question="Will the Fed cut rates in June?",
        category="crypto",
        market_probability=0.45,
        oracle_probability=0.58,
        edge=0.13,
        edge_abs=0.13,
        band="A",
        band_score=0.72,
        liquidity_score=0.75,
        volatility_score=0.50,
        catalyst_score=0.60,
        sentiment_score=0.55,
        correlation_score=0.50,
        trend_score=0.60,
        volume_24h=120_000,
        open_interest=250_000,
        bid=0.44,
        ask=0.46,
        spread=0.02,
        days_to_resolution=30.0,
        data_sources=["polymarket"],
        staleness_seconds=45,
        source_trust_score=0.90,
        pythia_snapshot_at=datetime.now(timezone.utc),
    )
