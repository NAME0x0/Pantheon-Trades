# Thesis Schema

A Thesis is the structured output of a Boule deliberation. It represents a council-approved investment hypothesis ready for Areopagus review.

## Full Schema

```python
class AgentVote(BaseModel):
    agent: str                        # Agent name (lowercase)
    vote: Literal["APPROVE", "REJECT", "ABSTAIN"]
    confidence: float                 # 0.0 - 1.0
    probability_estimate: float       # Agent's probability for YES
    flags: list[str]                  # Any flags raised (e.g., "cassandra_warning")
    summary: str                      # 1-2 sentence reasoning

class ExitConditions(BaseModel):
    invalidation: str                 # Prose description of invalidation scenario
    target: float                     # Exit probability (take profit)
    stop: float                       # Exit probability (stop loss)
    max_hold_days: int                # Maximum holding period
    recheck_triggers: list[str]       # Events that trigger early recheck

class ThesisBlock(BaseModel):
    agent: str
    round: int                        # 1-4
    content: str                      # Full agent reasoning text
    tokens: int
    latency_ms: int

class Thesis(BaseModel):
    # Identity
    thesis_id: str                    # uuid4
    signal_id: str                    # Source Signal
    market_id: str                    # Polymarket condition ID
    
    # Market
    question: str
    direction: Literal["YES", "NO"]
    
    # Council output
    council_probability: float        # Weighted consensus probability
    raw_market_probability: float     # Polymarket price at time of deliberation
    edge: float                       # council_probability - market_probability
    confidence: float                 # Council confidence (0.0 - 1.0)
    
    # Position sizing (recommendation; Areopagus may resize)
    recommended_size_pct: float       # % of portfolio (pre-Kelly)
    kelly_fraction: float             # Full Kelly fraction (computed by Areopagus)
    
    # Exit conditions
    exit_conditions: ExitConditions
    
    # Council votes
    agents: list[AgentVote]
    vote_summary: dict                # {"APPROVE": n, "REJECT": n, "ABSTAIN": n}
    weighted_approval: float          # Weighted approval fraction
    
    # Veto flags
    zeus_veto: bool
    solon_veto: bool
    cassandra_flags: list[str]
    humans_flags: list[str]
    hephaestus_flags: list[str]
    
    # Trace
    trace_id: str                     # Links to full debate trace
    debate_blocks: list[ThesisBlock]  # Per-agent per-round outputs
    
    # Timing
    deliberation_start: datetime
    deliberation_end: datetime
    deliberation_duration_ms: int
    
    # Status
    status: Literal[
        "pending_areopagus",
        "approved",
        "rejected",
        "expired",
        "executed",
        "cancelled"
    ]
    areopagus_decision: str | None    # "APPROVED" | "REJECTED" | "RESIZED"
    areopagus_note: str | None
    final_size_pct: float | None      # After Areopagus sizing
    
    created_at: datetime
    archived_cid: str | None          # IPFS CID after Parthenon archives
```

## Status Transitions

```
signal received
    │
    ▼
deliberation runs
    │
    ▼
pending_areopagus ──► rejected (veto or failed vote)
    │
    ▼
Areopagus review ──► rejected (risk gate failure)
    │                └► resized (approved with smaller size)
    ▼
approved ──► expired (if not executed within 15 min)
    │
    ▼
executed ──► (Argos monitors position)
    │
    └► cancelled (Argos exit or manual cancel)
```

## On-Chain Registration

When a Thesis reaches `approved` status, Parthenon calls `ThesisRegistry.register()` on-chain with:
- `thesisHash` = keccak256(thesis_id + market_id + council_probability + direction)
- `timestamp`
- `agentPassportIds[]` for all participating council members

This creates an immutable record that the thesis was approved before execution.

## Thesis Archive

After resolution, Parthenon archives the full Thesis JSON to IPFS, records the CID in `archived_cid`, and includes it in the daily Merkle root anchored on Arc Testnet.

See `docs/PARTHENON.md` and `docs/SETTLEMENT_FLOW.md`.
