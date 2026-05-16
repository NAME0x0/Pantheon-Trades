"""Tests for model-drift + cost-ledger telemetry."""

from __future__ import annotations

import asyncio
import time

import pytest

from boule.telemetry import (
    CostLedger,
    CostRow,
    DriftTracker,
    PRICING,
)


# ─── Drift ───────────────────────────────────────────────────────────


def test_first_fingerprint_blesses():
    t = DriftTracker()
    assert t.observe("anthropic/claude-sonnet-4-6") is None
    assert t.blessed == "anthropic/claude-sonnet-4-6"


def test_same_fingerprint_no_drift():
    t = DriftTracker()
    t.observe("anthropic/claude-sonnet-4-6")
    for _ in range(50):
        assert t.observe("anthropic/claude-sonnet-4-6") is None


def test_drift_triggers_at_threshold():
    t = DriftTracker()
    t.observe("anthropic/claude-sonnet-4-6")
    # 30 same + 30 different = 50% mismatch -> well above default 20%.
    for _ in range(30):
        t.observe("anthropic/claude-sonnet-4-6")
    event = None
    for _ in range(30):
        event = t.observe("anthropic/claude-sonnet-4-7") or event
    assert event is not None
    assert event["type"] == "model_drift"
    assert "mismatched_fraction" in event


def test_drift_resets_blessed_after_event():
    """Subsequent observations should not keep firing."""
    t = DriftTracker()
    t.observe("a")
    for _ in range(40):
        t.observe("a")
    for _ in range(40):
        t.observe("b")
    # First drift event should have fired; window cleared; b is now blessed.
    assert t.blessed in ("a", "b")
    # Continuing to observe "b" should not fire again.
    assert t.observe("b") is None


# ─── Cost ledger ─────────────────────────────────────────────────────


def test_estimate_usd_known_model():
    led = CostLedger()
    # 1M input + 1M output of sonnet ≈ $18
    usd = led.estimate_usd("claude-sonnet-4-6", 1_000_000, 1_000_000)
    assert 17.0 <= usd <= 19.0


def test_estimate_usd_unknown_model_conservative():
    led = CostLedger()
    usd = led.estimate_usd("brand-new-model", 1_000_000, 0)
    # Conservative default = $1 per 1M total tokens.
    assert 0.9 <= usd <= 1.1


def test_record_and_per_thesis_rollup():
    led = CostLedger()

    async def go():
        for i in range(3):
            await led.record(
                CostRow(
                    thesis_id="t1",
                    signal_id="s1",
                    agent=f"a{i}",
                    round=1,
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    tokens_in=1000,
                    tokens_out=1000,
                    usd=0.018,
                    timestamp=time.time(),
                )
            )
        await led.record(
            CostRow(
                thesis_id="t2",
                signal_id="s2",
                agent="ares",
                round=1,
                provider="anthropic",
                model="claude-sonnet-4-6",
                tokens_in=2000,
                tokens_out=500,
                usd=0.0135,
                timestamp=time.time(),
            )
        )

    asyncio.run(go())

    t1 = led.per_thesis_breakdown("t1")
    assert t1["n_calls"] == 3
    assert t1["total_usd"] == pytest.approx(0.054, abs=1e-4)
    assert set(t1["by_agent_usd"].keys()) == {"a0", "a1", "a2"}

    t2 = led.thesis_cost_usd("t2")
    assert t2 == pytest.approx(0.0135, abs=1e-4)

    # Unknown thesis returns 0
    assert led.thesis_cost_usd("never") == 0.0


def test_pricing_table_well_formed():
    for model, rate in PRICING.items():
        assert isinstance(rate, tuple) and len(rate) == 2
        inp, out = rate
        assert inp > 0 and out > 0, f"{model} has non-positive rate"
        assert out >= inp, f"{model} output rate {out} < input rate {inp} (unusual)"
