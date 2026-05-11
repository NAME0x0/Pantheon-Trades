# Underworld — Failure Analysis

The Underworld (Κάτω Κόσμος) in Greek mythology was the realm of the dead. In Pantheon Trades, the Underworld is where failed strategies, failed theses, and agent errors are cataloged, autopsied, and learned from.

## Components

`services/underworld/`:

### `graveyard.py` — Terminated Strategy Archive
Stores all terminated strategies with their full history:
- Entry criteria used
- Exit criteria
- Performance metrics (total PnL, Sharpe, Brier contributions)
- Termination reason and date
- Link to all associated theses

Searchable by termination reason, date, strategy type, performance quartile.

### `postmortem.py` — Post-Mortem Analysis
Structured analysis run for every terminated strategy and every thesis that resolved against prediction:

```python
class PostMortem(BaseModel):
    subject_id: str          # thesis_id or strategy_id
    subject_type: str        # "thesis" | "strategy"
    
    what_happened: str       # Factual description of the failure
    what_was_predicted: str  # What the thesis/strategy expected
    what_actually_happened: str  # Actual market outcome
    
    broken_assumptions: list[str]   # Which assumptions were wrong
    early_warning_signs: list[str]  # Signs that were present but ignored
    agent_accuracy: dict[str, float]  # Per-agent prediction accuracy
    
    cassandra_vindication: bool  # Did Cassandra warn about this?
    humans_flag_ignored: bool    # Was a Humans flag dismissed?
    
    lessons: list[str]       # Actionable lessons extracted
    priority: str            # "high" | "medium" | "low"
    
    created_at: datetime
    archived_cid: str
```

Post-mortems are automatically triggered for:
- Any thesis that resolved with PnL < -30% of capital risked
- Any strategy terminated due to performance
- Any strategy hit by drawdown limit

Manual post-mortems can be triggered for any thesis.

### `hallucination_log.py` — Agent Hallucination Tracker
Detects when agents assert facts that are contradicted by observable data:

Examples:
- Agent claims "volume has spiked 200%" but Pythia data shows -5%
- Agent references an event that did not happen
- Agent states "market has priced in X" but current probability contradicts this

Detection method:
1. Each `agent_output` TraceEvent is parsed for factual claims
2. Claims are cross-referenced against the shared Signal context
3. Contradictions flagged in `hallucination_log` table
4. Persistent hallucinators flagged to Ostrakon for calibration review

### `broken_assumptions.py` — Assumption Tracker
Catalogs recurring broken assumptions across all post-mortems:

```python
class BrokenAssumption(BaseModel):
    assumption: str          # The assumption that was wrong
    frequency: int           # How many times this assumption was wrong
    first_seen: datetime
    last_seen: datetime
    categories: list[str]    # Market categories where this failed
    associated_agents: list[str]  # Agents who held this assumption
```

Broken assumptions are extracted from post-mortems and fed back to Boule memory as "known failure patterns."

### `lessons.py` — Lesson Extraction
Extracts actionable lessons from post-mortems and makes them available to Boule:

```python
async def get_relevant_lessons(market_category: str, market_type: str) -> list[str]:
    # Returns top-5 most relevant lessons for this market type
    # Based on similarity to current signal context
```

Boule includes top lessons in the Messengers agent context at the start of each deliberation.

## Lesson Feedback Loop

```
Failed thesis
    │
    ▼
Post-mortem created
    │
    ▼
Lessons extracted
    │
    ▼
Stored in Boule memory
    │
    ▼
Future deliberations include relevant lessons
```

This creates an institutional memory — the system "remembers" why previous similar trades failed.

## On-Chain

`Underworld.sol` records:
- Post-mortem summary hashes
- Lesson CIDs (IPFS)
- Strategy termination records

All immutably anchored for external auditability.
