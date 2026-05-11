# Trace Format

Every Boule deliberation emits a structured trace. Traces are the primary audit mechanism — they let you reconstruct exactly what each agent said, when, and why the council reached its verdict.

## TraceEvent Schema

```python
class TraceEvent(BaseModel):
    trace_id: str              # Shared across all events in one deliberation
    event_id: str              # uuid4, unique per event
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
        "archive"
    ]
    
    # Agent context (null for system events)
    agent: str | None
    round: int | None          # 1-4
    
    # Content
    content: str               # Full text output from agent or system message
    tokens: int | None         # Token count for LLM events
    latency_ms: int | None
    
    # Structured outputs (for vote/verdict events)
    vote: Literal["APPROVE", "REJECT", "ABSTAIN"] | None
    confidence: float | None
    probability_estimate: float | None
    flags: list[str]
    
    timestamp: datetime
    sequence: int              # Monotonically increasing within trace
```

## Event Types

### `deliberation_start`
Emitted when Boule receives a Signal and begins deliberation.
```json
{
  "event_type": "deliberation_start",
  "content": "Starting deliberation for market 0xabc... (question: 'Will X?', edge: +0.12, band: A)",
  "agent": null
}
```

### `agent_output`
Emitted for each agent in each round.
```json
{
  "event_type": "agent_output",
  "agent": "hades",
  "round": 1,
  "content": "From the depths of worst-case analysis...\n\n[full reasoning text]",
  "tokens": 312,
  "latency_ms": 1840,
  "probability_estimate": 0.61
}
```

### `veto`
Emitted when Zeus or Solon casts a veto. Ends deliberation immediately.
```json
{
  "event_type": "veto",
  "agent": "solon",
  "content": "This thesis violates RISK_POLICY.md Article II: max_hold_days 120 exceeds policy limit of 90.",
  "vote": "REJECT",
  "flags": ["policy_violation:max_hold_days"]
}
```

### `flag`
Emitted when Cassandra, Humans, or Hephaestus raises a non-veto flag.
```json
{
  "event_type": "flag",
  "agent": "cassandra",
  "content": "Warning: regulatory announcement risk. SEC decision expected during hold period.",
  "flags": ["regulatory_risk", "tail_risk_identified"]
}
```

### `synthesis`
Athena's Round 3 synthesis output.
```json
{
  "event_type": "synthesis",
  "agent": "athena",
  "round": 3,
  "content": "Council synthesis: Bull case centers on... Bear case flags... Net assessment..."
}
```

### `verdict`
Final council outcome.
```json
{
  "event_type": "verdict",
  "content": "APPROVED",
  "vote": "APPROVE",
  "confidence": 0.78,
  "probability_estimate": 0.72,
  "flags": ["cassandra_warning:regulatory_risk"]
}
```

### `areopagus_decision`
Areopagus result after risk gating.
```json
{
  "event_type": "areopagus_decision",
  "content": "APPROVED with resize: 5% → 3.2% (half-Kelly constraint)",
  "flags": ["resized"]
}
```

## Trace Storage

Traces are:
1. Streamed to web UI via WebSocket in real-time (during deliberation)
2. Written to PostgreSQL for fast API queries
3. Archived to IPFS by Parthenon (full JSON)
4. Linked in `Thesis.trace_id`

Trace CID is recorded in `ThesisRegistry.sol` on-chain.

## Viewing Traces

Web UI: `/traces` — searchable list of all deliberations
Web UI: `/traces/{trace_id}` — full debate viewer with per-agent, per-round timeline

API: `GET /api/traces/{trace_id}`

## Retention

Traces are retained indefinitely in IPFS/Irys. PostgreSQL traces older than 90 days are pruned (the IPFS archive is the permanent record).
