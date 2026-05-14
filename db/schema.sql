-- Pantheon Trades initial schema.
-- Apply with: psql $DATABASE_URL -f db/schema.sql

CREATE TABLE IF NOT EXISTS signals (
    signal_id              TEXT PRIMARY KEY,
    market_id              TEXT NOT NULL,
    question               TEXT NOT NULL,
    category               TEXT NOT NULL,
    market_probability     DOUBLE PRECISION NOT NULL,
    oracle_probability     DOUBLE PRECISION NOT NULL,
    edge                   DOUBLE PRECISION NOT NULL,
    edge_abs               DOUBLE PRECISION NOT NULL,
    band                   TEXT NOT NULL,
    band_score             DOUBLE PRECISION NOT NULL,
    liquidity_score        DOUBLE PRECISION NOT NULL,
    volatility_score       DOUBLE PRECISION NOT NULL,
    catalyst_score         DOUBLE PRECISION NOT NULL,
    sentiment_score        DOUBLE PRECISION NOT NULL,
    correlation_score      DOUBLE PRECISION NOT NULL,
    trend_score            DOUBLE PRECISION NOT NULL,
    volume_24h             DOUBLE PRECISION NOT NULL,
    open_interest          DOUBLE PRECISION NOT NULL,
    bid                    DOUBLE PRECISION NOT NULL,
    ask                    DOUBLE PRECISION NOT NULL,
    spread                 DOUBLE PRECISION NOT NULL,
    resolution_date        TIMESTAMPTZ,
    days_to_resolution     DOUBLE PRECISION,
    data_sources           JSONB NOT NULL DEFAULT '[]',
    staleness_seconds      INTEGER NOT NULL,
    source_trust_score     DOUBLE PRECISION NOT NULL,
    pythia_snapshot_at     TIMESTAMPTZ NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_signals_market_id ON signals (market_id);
CREATE INDEX IF NOT EXISTS ix_signals_band ON signals (band);
CREATE INDEX IF NOT EXISTS ix_signals_edge_abs ON signals (edge_abs);
CREATE INDEX IF NOT EXISTS ix_signals_created_at ON signals (created_at DESC);

CREATE TABLE IF NOT EXISTS theses (
    thesis_id                 TEXT PRIMARY KEY,
    signal_id                 TEXT NOT NULL REFERENCES signals(signal_id),
    market_id                 TEXT NOT NULL,
    question                  TEXT NOT NULL,
    direction                 TEXT NOT NULL,
    council_probability       DOUBLE PRECISION NOT NULL,
    raw_market_probability    DOUBLE PRECISION NOT NULL,
    edge                      DOUBLE PRECISION NOT NULL,
    confidence                DOUBLE PRECISION NOT NULL,
    recommended_size_pct      DOUBLE PRECISION NOT NULL,
    kelly_fraction            DOUBLE PRECISION NOT NULL DEFAULT 0,
    exit_conditions           JSONB NOT NULL,
    agents                    JSONB NOT NULL DEFAULT '[]',
    vote_summary              JSONB NOT NULL DEFAULT '{}',
    weighted_approval         DOUBLE PRECISION NOT NULL DEFAULT 0,
    zeus_veto                 BOOLEAN NOT NULL DEFAULT FALSE,
    solon_veto                BOOLEAN NOT NULL DEFAULT FALSE,
    cassandra_flags           JSONB NOT NULL DEFAULT '[]',
    humans_flags              JSONB NOT NULL DEFAULT '[]',
    hephaestus_flags          JSONB NOT NULL DEFAULT '[]',
    trace_id                  TEXT NOT NULL,
    debate_blocks             JSONB NOT NULL DEFAULT '[]',
    deliberation_start        TIMESTAMPTZ NOT NULL,
    deliberation_end          TIMESTAMPTZ NOT NULL,
    deliberation_duration_ms  INTEGER NOT NULL DEFAULT 0,
    status                    TEXT NOT NULL,
    areopagus_decision        TEXT,
    areopagus_note            TEXT,
    final_size_pct            DOUBLE PRECISION,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_cid              TEXT
);
CREATE INDEX IF NOT EXISTS ix_theses_market_id ON theses (market_id);
CREATE INDEX IF NOT EXISTS ix_theses_confidence ON theses (confidence DESC);
CREATE INDEX IF NOT EXISTS ix_theses_status ON theses (status);
CREATE INDEX IF NOT EXISTS ix_theses_trace_id ON theses (trace_id);
CREATE INDEX IF NOT EXISTS ix_theses_archived_cid ON theses (archived_cid);
CREATE INDEX IF NOT EXISTS ix_theses_created_at ON theses (created_at DESC);

CREATE TABLE IF NOT EXISTS trace_events (
    event_id              TEXT PRIMARY KEY,
    trace_id              TEXT NOT NULL,
    thesis_id             TEXT NOT NULL,
    signal_id             TEXT NOT NULL,
    market_id             TEXT NOT NULL,
    event_type            TEXT NOT NULL,
    agent                 TEXT,
    round                 INTEGER,
    content               TEXT NOT NULL,
    tokens                INTEGER,
    latency_ms            INTEGER,
    vote                  TEXT,
    confidence            DOUBLE PRECISION,
    probability_estimate  DOUBLE PRECISION,
    flags                 JSONB NOT NULL DEFAULT '[]',
    timestamp             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sequence              BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_trace_events_trace_id ON trace_events (trace_id, sequence);
CREATE INDEX IF NOT EXISTS ix_trace_events_thesis_id ON trace_events (thesis_id);
CREATE INDEX IF NOT EXISTS ix_trace_events_signal_id ON trace_events (signal_id);
CREATE INDEX IF NOT EXISTS ix_trace_events_event_type ON trace_events (event_type);
CREATE INDEX IF NOT EXISTS ix_trace_events_timestamp ON trace_events (timestamp DESC);

CREATE TABLE IF NOT EXISTS approval_tokens (
    token_id        TEXT PRIMARY KEY,
    thesis_id       TEXT NOT NULL,
    decision        TEXT NOT NULL,
    reason_code     TEXT NOT NULL,
    note            TEXT NOT NULL,
    final_size_pct  DOUBLE PRECISION,
    kelly_fraction  DOUBLE PRECISION,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_approval_tokens_thesis_id ON approval_tokens (thesis_id);
CREATE INDEX IF NOT EXISTS ix_approval_tokens_decision ON approval_tokens (decision);
CREATE INDEX IF NOT EXISTS ix_approval_tokens_created_at ON approval_tokens (created_at DESC);

CREATE TABLE IF NOT EXISTS rejection_records (
    record_id    TEXT PRIMARY KEY,
    thesis_id    TEXT NOT NULL,
    reason_code  TEXT NOT NULL,
    note         TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_rejection_records_thesis_id ON rejection_records (thesis_id);
CREATE INDEX IF NOT EXISTS ix_rejection_records_reason_code ON rejection_records (reason_code);
CREATE INDEX IF NOT EXISTS ix_rejection_records_created_at ON rejection_records (created_at DESC);

CREATE TABLE IF NOT EXISTS trades (
    trade_id            TEXT PRIMARY KEY,
    thesis_id           TEXT NOT NULL REFERENCES theses(thesis_id),
    market_id           TEXT NOT NULL,
    direction           TEXT NOT NULL,
    size_pct            DOUBLE PRECISION NOT NULL,
    size_usdc           DOUBLE PRECISION NOT NULL,
    entry_price         DOUBLE PRECISION NOT NULL,
    status              TEXT NOT NULL,
    order_id            TEXT,
    fill_price          DOUBLE PRECISION,
    fill_time           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_price       DOUBLE PRECISION,
    realised_pnl_usdc   DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS ix_trades_market_id ON trades (market_id);
CREATE INDEX IF NOT EXISTS ix_trades_status ON trades (status);
CREATE INDEX IF NOT EXISTS ix_trades_created_at ON trades (created_at DESC);

CREATE TABLE IF NOT EXISTS agent_metrics (
    agent               TEXT PRIMARY KEY,
    predictions         INTEGER NOT NULL DEFAULT 0,
    brier_score         DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    sharpe              DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    credibility_weight  DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    last_brier_inputs   JSONB NOT NULL DEFAULT '[]',
    last_returns        JSONB NOT NULL DEFAULT '[]',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_metrics_updated_at ON agent_metrics (updated_at DESC);

CREATE TABLE IF NOT EXISTS archive_manifests (
    manifest_cid          TEXT PRIMARY KEY,
    thesis_id             TEXT NOT NULL,
    market_id             TEXT NOT NULL,
    merkle_root           TEXT NOT NULL,
    entries               JSONB NOT NULL DEFAULT '[]',
    anchor_tx_hash        TEXT,
    anchor_block_number   BIGINT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_archive_manifests_thesis_id ON archive_manifests (thesis_id);
CREATE INDEX IF NOT EXISTS ix_archive_manifests_market_id ON archive_manifests (market_id);
CREATE INDEX IF NOT EXISTS ix_archive_manifests_merkle_root ON archive_manifests (merkle_root);
CREATE INDEX IF NOT EXISTS ix_archive_manifests_anchor_tx ON archive_manifests (anchor_tx_hash);
CREATE INDEX IF NOT EXISTS ix_archive_manifests_created_at ON archive_manifests (created_at DESC);

CREATE TABLE IF NOT EXISTS proof_of_restraint (
    proof_id     TEXT PRIMARY KEY,
    signal_id    TEXT NOT NULL,
    market_id    TEXT NOT NULL,
    reason_code  TEXT NOT NULL,
    note         TEXT NOT NULL,
    signal_hash  TEXT NOT NULL,
    tx_hash      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_por_signal_id ON proof_of_restraint (signal_id);
CREATE INDEX IF NOT EXISTS ix_por_market_id ON proof_of_restraint (market_id);
CREATE INDEX IF NOT EXISTS ix_por_reason_code ON proof_of_restraint (reason_code);
CREATE INDEX IF NOT EXISTS ix_por_created_at ON proof_of_restraint (created_at DESC);
