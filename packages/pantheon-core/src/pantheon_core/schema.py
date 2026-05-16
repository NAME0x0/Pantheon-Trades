"""Canonical wire-format schemas for Pantheon Trades.

Every model here is JSON-serialisable and round-trip safe through Redis,
Postgres, IPFS, and the FastAPI gateway. Avoid adding service-specific fields:
keep this module narrow so each service can depend on it without dragging in
unrelated logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

UTC = timezone.utc


def utc_now() -> datetime:
    """Timezone-aware UTC timestamp factory. Replaces deprecated datetime.utcnow."""
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


# ---------------------------------------------------------------------------
# Signal (Apollo -> Boule)
# ---------------------------------------------------------------------------


class Signal(BaseModel):
    signal_id: str = Field(default_factory=_uuid)
    market_id: str
    question: str
    category: Literal["crypto", "politics", "sports", "science", "other"]

    market_probability: float
    oracle_probability: float
    edge: float
    edge_abs: float

    band: Literal["S", "A", "B", "C", "D"]
    band_score: float

    liquidity_score: float
    volatility_score: float
    catalyst_score: float
    sentiment_score: float
    correlation_score: float
    trend_score: float

    volume_24h: float
    open_interest: float
    bid: float
    ask: float
    spread: float
    resolution_date: datetime | None = None
    days_to_resolution: float | None = None

    data_sources: list[str]
    staleness_seconds: int
    source_trust_score: float

    created_at: datetime = Field(default_factory=utc_now)
    pythia_snapshot_at: datetime

    @field_validator(
        "market_probability",
        "oracle_probability",
        "liquidity_score",
        "volatility_score",
        "catalyst_score",
        "sentiment_score",
        "correlation_score",
        "trend_score",
        "source_trust_score",
    )
    @classmethod
    def _clamp_probability_like(cls, v: float) -> float:
        return _clamp01(v)

    @field_validator("edge_abs")
    @classmethod
    def _edge_abs_non_negative(cls, v: float) -> float:
        return abs(v)


# ---------------------------------------------------------------------------
# Thesis components
# ---------------------------------------------------------------------------


class AgentVote(BaseModel):
    agent: str
    vote: Literal["APPROVE", "REJECT", "ABSTAIN"]
    confidence: float
    probability_estimate: float
    flags: list[str] = Field(default_factory=list)
    summary: str

    @field_validator("confidence", "probability_estimate")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return _clamp01(v)


class ExitConditions(BaseModel):
    invalidation: str
    target: float
    stop: float
    max_hold_days: int
    recheck_triggers: list[str] = Field(default_factory=list)


class ThesisBlock(BaseModel):
    agent: str
    round: int
    content: str
    tokens: int
    latency_ms: int


class Thesis(BaseModel):
    thesis_id: str = Field(default_factory=_uuid)
    signal_id: str
    market_id: str

    question: str
    direction: Literal["YES", "NO"]

    council_probability: float
    raw_market_probability: float
    edge: float
    confidence: float

    recommended_size_pct: float
    kelly_fraction: float = 0.0

    exit_conditions: ExitConditions

    agents: list[AgentVote] = Field(default_factory=list)
    vote_summary: dict[str, int] = Field(default_factory=dict)
    weighted_approval: float = 0.0

    zeus_veto: bool = False
    solon_veto: bool = False
    cassandra_flags: list[str] = Field(default_factory=list)
    humans_flags: list[str] = Field(default_factory=list)
    hephaestus_flags: list[str] = Field(default_factory=list)

    trace_id: str = Field(default_factory=_uuid)
    debate_blocks: list[ThesisBlock] = Field(default_factory=list)

    deliberation_start: datetime = Field(default_factory=utc_now)
    deliberation_end: datetime = Field(default_factory=utc_now)
    deliberation_duration_ms: int = 0

    status: Literal[
        "pending_areopagus",
        "approved",
        "rejected",
        "expired",
        "executed",
        "cancelled",
    ] = "pending_areopagus"
    areopagus_decision: str | None = None
    areopagus_note: str | None = None
    final_size_pct: float | None = None

    created_at: datetime = Field(default_factory=utc_now)
    archived_cid: str | None = None

    @field_validator("council_probability", "raw_market_probability", "confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return _clamp01(v)

    @property
    def signed_edge(self) -> float:
        """Direction-aware edge magnitude (always >= 0 for an actionable thesis)."""
        if self.direction == "YES":
            return self.council_probability - self.raw_market_probability
        return self.raw_market_probability - self.council_probability


# ---------------------------------------------------------------------------
# Trace events (Boule -> Parthenon / web UI)
# ---------------------------------------------------------------------------


class TraceEvent(BaseModel):
    trace_id: str
    event_id: str = Field(default_factory=_uuid)
    thesis_id: str
    signal_id: str
    market_id: str

    event_type: Literal[
        "deliberation_start",
        "agent_round_start",
        "agent_output",
        "agent_round_end",
        "veto",
        "flag",
        "synthesis",
        "vote",
        "verdict",
        "deliberation_end",
        "areopagus_decision",
        "execution_start",
        "execution_end",
        "archive",
        # ── Tier 2 / 3 telemetry event types ──
        "diversity",
        "reflection",
        "zeus_consensus_override",
        "model_drift",
    ]

    agent: str | None = None
    round: int | None = None

    content: str
    tokens: int | None = None
    latency_ms: int | None = None

    vote: Literal["APPROVE", "REJECT", "ABSTAIN"] | None = None
    confidence: float | None = None
    probability_estimate: float | None = None
    flags: list[str] = Field(default_factory=list)

    timestamp: datetime = Field(default_factory=utc_now)
    sequence: int = 0


# ---------------------------------------------------------------------------
# Areopagus outputs
# ---------------------------------------------------------------------------


class ApprovalToken(BaseModel):
    token_id: str = Field(default_factory=_uuid)
    thesis_id: str
    decision: Literal["APPROVED", "REJECTED", "RESIZED"]
    reason_code: str
    note: str
    final_size_pct: float | None = None
    kelly_fraction: float | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RejectionRecord(BaseModel):
    record_id: str = Field(default_factory=_uuid)
    thesis_id: str
    reason_code: str
    note: str
    created_at: datetime = Field(default_factory=utc_now)


# ---------------------------------------------------------------------------
# Trade and exits
# ---------------------------------------------------------------------------


class Trade(BaseModel):
    trade_id: str = Field(default_factory=_uuid)
    thesis_id: str
    market_id: str
    direction: Literal["YES", "NO"]
    size_pct: float
    size_usdc: float
    entry_price: float
    status: Literal["pending", "filled", "partial", "cancelled", "failed"] = "pending"
    order_id: str | None = None
    fill_price: float | None = None
    fill_time: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ExitSignal(BaseModel):
    signal_id: str = Field(default_factory=_uuid)
    trade_id: str
    market_id: str
    reason: Literal["target_hit", "stop_loss", "invalidation", "areopagus_override", "manual", "expiry"]
    current_price: float
    created_at: datetime = Field(default_factory=utc_now)
