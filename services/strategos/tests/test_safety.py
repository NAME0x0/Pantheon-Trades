"""Tests for the live-mode safety wrapper.

We use an in-memory fake Redis so the gate logic is exercised against
a deterministic state map rather than a real connection.
"""

from __future__ import annotations

import asyncio
from typing import Any


from pantheon_core.schema import ApprovalToken, Thesis
from strategos.safety import (
    GuardDecision,
    SafetyWrapper,
    APPROVED_FLAG_ENV,
    CONSEC_LOSSES_KEY,
)


class _FakeRedis:
    """Tiny key-value store mimicking the subset of aioredis we use."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: Any) -> None:
        self.store[key] = str(value)

    async def incr(self, key: str) -> int:
        v = int(self.store.get(key) or 0) + 1
        self.store[key] = str(v)
        return v

    async def incrbyfloat(self, key: str, value: float) -> float:
        v = float(self.store.get(key) or 0.0) + value
        self.store[key] = str(v)
        return v

    async def expire(self, key: str, seconds: int) -> None:
        return None


def _token() -> ApprovalToken:
    return ApprovalToken(
        thesis_id="th-1",
        decision="RESIZED",
        reason_code="OK",
        note="",
        final_size_pct=0.05,
        kelly_fraction=0.375,
    )


def _thesis() -> Thesis:
    from pantheon_core.schema import ExitConditions

    return Thesis(
        thesis_id="th-1",
        signal_id="sig-1",
        market_id="0xtest",
        question="will x happen",
        direction="YES",
        council_probability=0.6,
        raw_market_probability=0.42,
        edge=0.18,
        confidence=0.7,
        recommended_size_pct=0.05,
        exit_conditions=ExitConditions(
            invalidation="n/a", target=0.7, stop=0.37, max_hold_days=30
        ),
        agents=[],
        vote_summary={"APPROVE": 8, "REJECT": 0, "ABSTAIN": 2},
        weighted_approval=0.8,
        zeus_veto=False,
        solon_veto=False,
        trace_id="trace-1",
        debate_blocks=[],
        status="pending_areopagus",
    )


def test_passes_when_clean(monkeypatch):
    monkeypatch.setenv(APPROVED_FLAG_ENV, "1")
    fake = _FakeRedis()
    w = SafetyWrapper(fake)
    out = asyncio.run(w.guard(_token(), _thesis()))
    assert out.decision == GuardDecision.PROCEED


def test_circuit_breaker_trips_at_threshold(monkeypatch):
    monkeypatch.setenv(APPROVED_FLAG_ENV, "1")
    fake = _FakeRedis()
    fake.store[CONSEC_LOSSES_KEY] = "3"
    w = SafetyWrapper(fake)
    out = asyncio.run(w.guard(_token(), _thesis()))
    assert out.decision == GuardDecision.PAPER_FALLBACK
    assert out.reason == "CIRCUIT_BREAKER"


def test_first_n_requires_manual_flag(monkeypatch):
    monkeypatch.delenv(APPROVED_FLAG_ENV, raising=False)
    fake = _FakeRedis()
    # No live trades yet — should block.
    w = SafetyWrapper(fake)
    out = asyncio.run(w.guard(_token(), _thesis()))
    assert out.decision == GuardDecision.AWAIT_MANUAL


def test_first_n_proceeds_with_flag(monkeypatch):
    monkeypatch.setenv(APPROVED_FLAG_ENV, "true")
    fake = _FakeRedis()
    w = SafetyWrapper(fake)
    out = asyncio.run(w.guard(_token(), _thesis()))
    assert out.decision == GuardDecision.PROCEED


def test_cost_cap_blocks(monkeypatch):
    monkeypatch.setenv(APPROVED_FLAG_ENV, "1")
    monkeypatch.setenv("STRATEGOS_DAILY_COST_CAP_USD", "5.00")

    # Re-import so the env var is picked up by the module-level constant.
    import importlib

    import strategos.safety as safety_module

    importlib.reload(safety_module)
    fake = _FakeRedis()
    from datetime import datetime, timezone

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fake.store[safety_module.COST_KEY_FMT.format(day=day)] = "5.50"
    w = safety_module.SafetyWrapper(fake)
    out = asyncio.run(w.guard(_token(), _thesis()))
    assert out.decision == safety_module.GuardDecision.COST_CAP_EXCEEDED


def test_quote_drift_aborts(monkeypatch):
    monkeypatch.setenv(APPROVED_FLAG_ENV, "1")
    fake = _FakeRedis()
    w = SafetyWrapper(fake)
    # Recorded ask 0.42, current ask 0.47 — drift 5pp, above default 3pp cap
    out = asyncio.run(
        w.guard(_token(), _thesis(), current_ask=0.47, recorded_ask=0.42)
    )
    assert out.decision == GuardDecision.QUOTE_DRIFT_ABORT


def test_quote_drift_within_tolerance_passes(monkeypatch):
    monkeypatch.setenv(APPROVED_FLAG_ENV, "1")
    fake = _FakeRedis()
    w = SafetyWrapper(fake)
    out = asyncio.run(
        w.guard(_token(), _thesis(), current_ask=0.43, recorded_ask=0.42)
    )
    assert out.decision == GuardDecision.PROCEED


def test_record_settlement_resets_on_win(monkeypatch):
    fake = _FakeRedis()
    fake.store[CONSEC_LOSSES_KEY] = "2"
    w = SafetyWrapper(fake)
    asyncio.run(w.record_settlement(pnl_usdc=15.0))
    assert fake.store[CONSEC_LOSSES_KEY] == "0"


def test_record_settlement_increments_on_loss(monkeypatch):
    fake = _FakeRedis()
    fake.store[CONSEC_LOSSES_KEY] = "1"
    w = SafetyWrapper(fake)
    asyncio.run(w.record_settlement(pnl_usdc=-20.0))
    assert fake.store[CONSEC_LOSSES_KEY] == "2"
