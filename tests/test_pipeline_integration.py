"""End-to-end pipeline test using in-memory fakes.

Exercises the full Pantheon flow without external services:

  Apollo MarketSnapshot
    -> Apollo score_market (builds Signal)
    -> Boule deliberate (fake Anthropic returns scripted votes)
    -> Areopagus court (gates the thesis + sizes via half-Kelly)
    -> Strategos paper book (executes the trade)
    -> Argos exit rules (target fires when price hits)

No network. No Redis. No live Anthropic. The test demonstrates every wire
boundary lines up — schemas round-trip and the modules compose cleanly.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (
    ROOT / "packages" / "pantheon-core" / "src",
    ROOT / "services" / "apollo" / "src",
    ROOT / "services" / "boule" / "src",
    ROOT / "services" / "areopagus" / "src",
    ROOT / "services" / "strategos" / "src",
    ROOT / "services" / "argos" / "src",
):
    sys.path.insert(0, str(p))


# ---------- helpers ---------------------------------------------------------


def _build_signal():
    from apollo.features.catalyst import CatalystEvent
    from apollo.features.sentiment import SentimentSample
    from apollo.scorer import MarketSnapshot, score_market

    snap = MarketSnapshot(
        market_id="0xtest_pipeline",
        question="Will pipeline complete end to end?",
        category="other",
        market_probability=0.40,
        bid=0.39,
        ask=0.41,
        volume_24h=400_000,
        open_interest=600_000,
        price_history=[0.30, 0.32, 0.36, 0.38, 0.40],
        price_std_24h=0.04,
        price_mean=0.36,
        catalysts=[CatalystEvent("decision", 12, 0.9)],
        sentiment_samples=[SentimentSample(0.6, 2.0)],
        data_sources=["polymarket"],
        snapshot_at=datetime.now(timezone.utc),
        staleness_seconds=10,
        source_trust_score=0.9,
        days_to_resolution=14.0,
        sentiment_adjustment=0.08,
        trend_adjustment=0.04,
        catalyst_adjustment=0.05,
    )
    return score_market(snap)


VOTE_TEXT = (
    "VOTE: APPROVE\n"
    "CONFIDENCE: 0.78\n"
    "PROBABILITY: 0.62\n"
    "FLAGS: NONE\n"
    "REASON: Edge is large and gates are clean."
)
NON_VOTE_TEXT = "Opening assessment: market mispriced, conviction medium-high."


class _FakeAnthropic:
    """LLMClient stub. Returns the structured vote block when the prompt
    asks for one, otherwise a generic opening/challenge text."""

    async def complete(self, *, system, messages, max_tokens):
        from boule.llm.base import CompletionResult

        user_text = messages[-1]["content"] if messages else ""
        text = VOTE_TEXT if "VOTE: APPROVE|REJECT|ABSTAIN" in user_text else NON_VOTE_TEXT
        return CompletionResult(text=text, tokens=280)

    async def close(self):
        return None


class _NullTracer:
    """No-op tracer that satisfies the Tracer interface without Redis."""

    def __init__(self):
        self.trace_id = "trace-0"
        self.thesis_id = "thesis-0"
        self.signal_id = "sig-0"
        self.market_id = "mkt-0"
        self._seq = 0
        self.events: list = []

    async def emit(self, event_type: str, content: str, **kwargs):
        from pantheon_core.schema import TraceEvent, utc_now

        self._seq += 1
        event = TraceEvent(
            trace_id=self.trace_id,
            thesis_id=self.thesis_id,
            signal_id=self.signal_id,
            market_id=self.market_id,
            event_type=event_type,  # type: ignore[arg-type]
            content=content,
            timestamp=utc_now(),
            sequence=self._seq,
            **{k: v for k, v in kwargs.items() if v is not None},
        )
        self.events.append(event)
        return event


# ---------- tests -----------------------------------------------------------


@pytest.mark.asyncio
async def test_signal_through_boule_areopagus_to_paper_trade():
    from areopagus.court import AreopagusCourt
    from areopagus.gates import PortfolioState
    from boule.debate import run_debate
    from pantheon_core.schema import ApprovalToken, RejectionRecord
    from strategos.paper import PaperBook

    signal = _build_signal()
    assert signal.band in ("S", "A", "B"), signal.band

    tracer = _NullTracer()
    tracer.signal_id = signal.signal_id
    tracer.market_id = signal.market_id

    thesis = await run_debate(
        signal=signal,
        client=_FakeAnthropic(),
        tracer=tracer,
        thesis_id="thesis-pipeline",
    )

    # Council approved with 60%+ weighted confidence; vetoes off.
    assert thesis.status == "pending_areopagus", thesis.status
    assert thesis.confidence >= 0.6
    assert thesis.direction in ("YES", "NO")
    assert not thesis.zeus_veto
    assert not thesis.solon_veto

    court = AreopagusCourt(portfolio=PortfolioState())
    verdict = court.evaluate_thesis(thesis, signal)
    assert isinstance(verdict, (ApprovalToken, RejectionRecord))
    if isinstance(verdict, RejectionRecord):
        pytest.fail(f"Areopagus rejected: {verdict.reason_code} {verdict.note}")

    assert verdict.decision in ("APPROVED", "RESIZED")
    assert verdict.final_size_pct and 0 < verdict.final_size_pct <= 0.05

    paper = PaperBook(portfolio_usdc=10_000.0)
    trade = paper.execute(verdict, thesis, mid_price=signal.market_probability, depth_usdc=200_000)
    assert trade.status == "filled"
    assert trade.direction == thesis.direction
    assert trade.fill_price is not None and 0 < trade.fill_price < 1

    # Settle on full win: payoff = 1 for the side we hold.
    pnl_win = paper.settle(trade.trade_id, resolution_yes_price=1.0 if thesis.direction == "YES" else 0.0)
    assert pnl_win > 0, "winning resolution must produce positive PnL"


@pytest.mark.asyncio
async def test_argos_exit_fires_on_target():
    from argos.exits import check_exit
    from argos.pnl import Position

    pos = Position(
        trade_id="t-int",
        market_id="m-int",
        direction="YES",
        entry_price=0.40,
        size_usdc=1_000.0,
        entered_at=datetime.now(timezone.utc) - timedelta(hours=1),
        target=0.55,
        stop=0.30,
        current_price=0.56,
    )
    sig = check_exit(pos)
    assert sig is not None and sig.reason == "target_hit"
