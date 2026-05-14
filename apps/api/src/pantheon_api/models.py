"""SQLAlchemy ORM models for Pantheon Trades.

Mirrors the wire-format schemas from ``pantheon_core.schema`` into Postgres
tables. The ORM layer is intentionally narrow: each row is the persistent
copy of an event the services emit over Redis streams. Heavy queries
(leaderboard, archive replay) read from these tables; live coordination
between services still goes through Redis.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from pantheon_core.schema import utc_now


class Base(DeclarativeBase):
    pass


def _ts() -> datetime:
    return utc_now()


# ---------------------------------------------------------------------------
# Signals (Apollo -> Boule)
# ---------------------------------------------------------------------------

class SignalRecord(Base):
    __tablename__ = "signals"

    signal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    market_id: Mapped[str] = mapped_column(String(96), index=True)
    question: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(16), index=True)

    market_probability: Mapped[float] = mapped_column(Float)
    oracle_probability: Mapped[float] = mapped_column(Float)
    edge: Mapped[float] = mapped_column(Float)
    edge_abs: Mapped[float] = mapped_column(Float, index=True)

    band: Mapped[str] = mapped_column(String(2), index=True)
    band_score: Mapped[float] = mapped_column(Float)

    liquidity_score: Mapped[float] = mapped_column(Float)
    volatility_score: Mapped[float] = mapped_column(Float)
    catalyst_score: Mapped[float] = mapped_column(Float)
    sentiment_score: Mapped[float] = mapped_column(Float)
    correlation_score: Mapped[float] = mapped_column(Float)
    trend_score: Mapped[float] = mapped_column(Float)

    volume_24h: Mapped[float] = mapped_column(Float)
    open_interest: Mapped[float] = mapped_column(Float)
    bid: Mapped[float] = mapped_column(Float)
    ask: Mapped[float] = mapped_column(Float)
    spread: Mapped[float] = mapped_column(Float)
    resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    days_to_resolution: Mapped[float | None] = mapped_column(Float, nullable=True)

    data_sources: Mapped[list] = mapped_column(JSON, default=list)
    staleness_seconds: Mapped[int] = mapped_column(Integer)
    source_trust_score: Mapped[float] = mapped_column(Float)

    pythia_snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)

    theses: Mapped[list["ThesisRecord"]] = relationship(back_populates="signal")


# ---------------------------------------------------------------------------
# Theses (Boule -> Areopagus)
# ---------------------------------------------------------------------------

class ThesisRecord(Base):
    __tablename__ = "theses"

    thesis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(64), ForeignKey("signals.signal_id"), index=True)
    market_id: Mapped[str] = mapped_column(String(96), index=True)

    question: Mapped[str] = mapped_column(Text)
    direction: Mapped[str] = mapped_column(String(4))

    council_probability: Mapped[float] = mapped_column(Float)
    raw_market_probability: Mapped[float] = mapped_column(Float)
    edge: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, index=True)

    recommended_size_pct: Mapped[float] = mapped_column(Float)
    kelly_fraction: Mapped[float] = mapped_column(Float, default=0.0)

    exit_conditions: Mapped[dict] = mapped_column(JSON)
    agents: Mapped[list] = mapped_column(JSON, default=list)
    vote_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    weighted_approval: Mapped[float] = mapped_column(Float, default=0.0, index=True)

    zeus_veto: Mapped[bool] = mapped_column(Boolean, default=False)
    solon_veto: Mapped[bool] = mapped_column(Boolean, default=False)
    cassandra_flags: Mapped[list] = mapped_column(JSON, default=list)
    humans_flags: Mapped[list] = mapped_column(JSON, default=list)
    hephaestus_flags: Mapped[list] = mapped_column(JSON, default=list)

    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    debate_blocks: Mapped[list] = mapped_column(JSON, default=list)

    deliberation_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deliberation_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deliberation_duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(24), index=True)
    areopagus_decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    areopagus_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_size_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)
    archived_cid: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)

    signal: Mapped[SignalRecord] = relationship(back_populates="theses")
    trades: Mapped[list["TradeRecord"]] = relationship(back_populates="thesis")


# ---------------------------------------------------------------------------
# Trace events
# ---------------------------------------------------------------------------

class TraceEventRecord(Base):
    __tablename__ = "trace_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    thesis_id: Mapped[str] = mapped_column(String(64), index=True)
    signal_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(96))

    event_type: Mapped[str] = mapped_column(String(32), index=True)
    agent: Mapped[str | None] = mapped_column(String(24), nullable=True)
    round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vote: Mapped[str | None] = mapped_column(String(8), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    probability_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    flags: Mapped[list] = mapped_column(JSON, default=list)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)
    sequence: Mapped[int] = mapped_column(BigInteger, default=0)


# ---------------------------------------------------------------------------
# Approval / rejection records
# ---------------------------------------------------------------------------

class ApprovalTokenRecord(Base):
    __tablename__ = "approval_tokens"

    token_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(16), index=True)
    reason_code: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text)
    final_size_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    kelly_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)


class RejectionRecordRow(Base):
    __tablename__ = "rejection_records"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(String(64), index=True)
    reason_code: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

class TradeRecord(Base):
    __tablename__ = "trades"

    trade_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(String(64), ForeignKey("theses.thesis_id"), index=True)
    market_id: Mapped[str] = mapped_column(String(96), index=True)
    direction: Mapped[str] = mapped_column(String(4))
    size_pct: Mapped[float] = mapped_column(Float)
    size_usdc: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), index=True)
    order_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)
    settled_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    realised_pnl_usdc: Mapped[float | None] = mapped_column(Float, nullable=True)

    thesis: Mapped[ThesisRecord] = relationship(back_populates="trades")


# ---------------------------------------------------------------------------
# Agent metrics (Ostrakon snapshot)
# ---------------------------------------------------------------------------

class AgentMetricsRecord(Base):
    __tablename__ = "agent_metrics"

    agent: Mapped[str] = mapped_column(String(24), primary_key=True)
    predictions: Mapped[int] = mapped_column(Integer, default=0)
    brier_score: Mapped[float] = mapped_column(Float, default=1.0)
    sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    credibility_weight: Mapped[float] = mapped_column(Float, default=1.0)
    last_brier_inputs: Mapped[list] = mapped_column(JSON, default=list)
    last_returns: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)


# ---------------------------------------------------------------------------
# Archive manifests
# ---------------------------------------------------------------------------

class ArchiveManifestRecord(Base):
    __tablename__ = "archive_manifests"

    manifest_cid: Mapped[str] = mapped_column(String(96), primary_key=True)
    thesis_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(96), index=True)
    merkle_root: Mapped[str] = mapped_column(String(66), index=True)
    entries: Mapped[list] = mapped_column(JSON, default=list)
    anchor_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
    anchor_block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)


# ---------------------------------------------------------------------------
# Proof of restraint
# ---------------------------------------------------------------------------

class ProofOfRestraintRecord(Base):
    __tablename__ = "proof_of_restraint"

    proof_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(64), index=True)
    market_id: Mapped[str] = mapped_column(String(96), index=True)
    reason_code: Mapped[str] = mapped_column(String(32), index=True)
    note: Mapped[str] = mapped_column(Text)
    signal_hash: Mapped[str] = mapped_column(String(66))
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ts, index=True)


__all__ = [
    "Base",
    "SignalRecord",
    "ThesisRecord",
    "TraceEventRecord",
    "ApprovalTokenRecord",
    "RejectionRecordRow",
    "TradeRecord",
    "AgentMetricsRecord",
    "ArchiveManifestRecord",
    "ProofOfRestraintRecord",
]
