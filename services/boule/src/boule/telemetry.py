"""LLM call telemetry — model drift detection + per-trade cost attribution.

Two facilities, both backed by the same in-memory ring + optional
Redis publication so multiple Boule workers share visibility.

  1. **Drift tracker** — record the provider's model identifier
     ("anthropic/claude-sonnet-4-6", "google/gemini-2.5-flash-lite",
     etc.) on every completion. Compare against a recorded "blessed"
     fingerprint; emit ``model_drift`` events when the fingerprint
     diverges for more than ``DRIFT_FRACTION_THRESHOLD`` of the recent
     window. Drift invalidates calibration — the calibrators were fit
     against a different model.

  2. **Cost ledger** — record (signal_id, thesis_id, agent, round,
     provider, model, tokens, usd) per completion. Aggregate via
     ``ledger.thesis_cost_usd(thesis_id)``. The pricing table is a
     dict in $/1M input + $/1M output tokens and updates as
     providers change rate cards.

Both are best-effort and fail open: a logging or Redis hiccup
must never block a council deliberation.
"""

from __future__ import annotations

import asyncio
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import structlog

log = structlog.get_logger("boule.telemetry")

# ─── Drift detection ─────────────────────────────────────────────────

DRIFT_FRACTION_THRESHOLD = float(os.environ.get("BOULE_DRIFT_FRACTION", "0.2"))
DRIFT_WINDOW_SIZE = int(os.environ.get("BOULE_DRIFT_WINDOW", "200"))


@dataclass
class DriftTracker:
    """Sliding-window fingerprint counter."""

    blessed: Optional[str] = None
    window: deque[str] = field(default_factory=lambda: deque(maxlen=DRIFT_WINDOW_SIZE))

    def observe(self, fingerprint: Optional[str]) -> Optional[dict]:
        """Record a new fingerprint. Returns a drift event dict when the
        recent window shows a mismatch over the threshold."""
        if not fingerprint:
            return None
        if self.blessed is None:
            self.blessed = fingerprint
            return None
        self.window.append(fingerprint)
        if len(self.window) < max(20, int(DRIFT_WINDOW_SIZE * 0.1)):
            return None
        mismatched = sum(1 for f in self.window if f != self.blessed)
        fraction = mismatched / max(1, len(self.window))
        if fraction >= DRIFT_FRACTION_THRESHOLD:
            event = {
                "type": "model_drift",
                "blessed": self.blessed,
                "recent_unique_fingerprints": sorted(set(self.window))[:5],
                "mismatched_fraction": round(fraction, 3),
                "window_size": len(self.window),
            }
            log.warning("boule.model_drift", **event)
            # Reset blessed to the new dominant fingerprint so we don't
            # alert continuously on the same drift event.
            counts: dict[str, int] = {}
            for f in self.window:
                counts[f] = counts.get(f, 0) + 1
            self.blessed = max(counts, key=counts.get)
            self.window.clear()
            return event
        return None


# Singleton — Boule imports + uses directly.
_drift = DriftTracker()


def record_fingerprint(fingerprint: Optional[str]) -> Optional[dict]:
    """Public API: returns a drift event dict when one fires."""
    event = _drift.observe(fingerprint)
    if event is not None:
        try:
            from boule.metrics import m as _pm

            _pm["drift_events_total"].inc()
        except Exception:  # noqa: BLE001
            pass
    return event


# ─── Cost ledger ─────────────────────────────────────────────────────

# Approx $/1M tokens. Update with provider rate cards.
PRICING: dict[str, tuple[float, float]] = {
    # (input_per_1m_usd, output_per_1m_usd)
    "claude-sonnet-4-6":           (3.0, 15.0),
    "claude-opus-4-7":             (15.0, 75.0),
    "claude-haiku-4-5":            (0.8, 4.0),
    "gemini-2.5-flash":            (0.075, 0.30),
    "gemini-2.5-flash-lite":       (0.04, 0.12),
    "gemini-2.5-pro":              (1.25, 5.0),
    "gpt-4o":                      (2.5, 10.0),
    "gpt-4o-mini":                 (0.15, 0.60),
    "deepseek-chat":               (0.27, 1.10),
    "grok-2-latest":               (2.0, 10.0),
    "llama-3.1-70b-versatile":     (0.59, 0.79),
}


@dataclass(frozen=True)
class CostRow:
    thesis_id: str
    signal_id: str
    agent: str
    round: int
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    usd: float
    timestamp: float


class CostLedger:
    def __init__(self) -> None:
        self._rows: list[CostRow] = []
        self._lock = asyncio.Lock()

    def estimate_usd(self, model: str, tokens_in: int, tokens_out: int) -> float:
        # Strip provider prefix the OpenRouter style uses (e.g.
        # "openai/gpt-4o" -> "gpt-4o").
        m = model.split("/")[-1]
        rate = PRICING.get(m)
        if rate is None:
            # Conservative default if we don't know the model.
            return ((tokens_in + tokens_out) / 1_000_000) * 1.0
        rin, rout = rate
        return (tokens_in / 1_000_000) * rin + (tokens_out / 1_000_000) * rout

    async def record(self, row: CostRow) -> None:
        async with self._lock:
            self._rows.append(row)
            # Cap in-memory ring at 5000 rows; older history must live
            # in the persistence layer.
            if len(self._rows) > 5000:
                self._rows = self._rows[-5000:]
        # Best-effort Prometheus emission. No-op without prometheus_client.
        try:
            from boule.metrics import m as _pm

            provider = row.provider or "unknown"
            _pm["llm_cost_usd_total"].labels(provider=provider).inc(row.usd)
            _pm["llm_calls_total"].labels(
                provider=provider, model=row.model or "unknown"
            ).inc()
        except Exception:  # noqa: BLE001
            pass

    def thesis_cost_usd(self, thesis_id: str) -> float:
        return sum(r.usd for r in self._rows if r.thesis_id == thesis_id)

    def per_thesis_breakdown(self, thesis_id: str) -> dict:
        rows = [r for r in self._rows if r.thesis_id == thesis_id]
        by_agent: dict[str, float] = {}
        total_in = total_out = 0
        for r in rows:
            by_agent[r.agent] = by_agent.get(r.agent, 0.0) + r.usd
            total_in += r.tokens_in
            total_out += r.tokens_out
        return {
            "thesis_id": thesis_id,
            "total_usd": round(sum(r.usd for r in rows), 6),
            "total_tokens_in": total_in,
            "total_tokens_out": total_out,
            "by_agent_usd": {k: round(v, 6) for k, v in by_agent.items()},
            "n_calls": len(rows),
        }


ledger = CostLedger()
