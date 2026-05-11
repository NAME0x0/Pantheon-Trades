# Boule — The Deliberation Council

The Boule (βουλή, "council") is the multi-agent deliberation system at the heart of Pantheon Trades. Named after the ancient Athenian council of 500 citizens, it convenes a panel of AI agents to debate every potential trade before execution.

## Design

No single agent controls the outcome. Every thesis requires a council majority plus Solon (compliance) and Zeus (constitutional) approval. The debate is adversarial by design — bear and bull agents argue opposing views, Cassandra surfaces tail risks, Hades stress-tests downside.

## Council Members

See `docs/AGENTS.md` for full descriptions.

| Agent | Archetype | Veto? |
|-------|-----------|-------|
| Zeus | Supreme authority | Yes — constitutional |
| Solon | Lawgiver / compliance | Yes — policy |
| Hades | Risk sovereign | No (2x weight) |
| Athena | Strategic wisdom | No (1.5x weight) |
| Apollo | Technical oracle | No |
| Cassandra | Prophetic warning | No (triggers AR review) |
| Ares | Bull advocate | No |
| Hephaestus | Execution mechanic | No (flags for review) |
| Themis | Justice / proportionality | No |
| Daedalus | Structural analyst | No |
| Strategos | Execution planner | No |
| Humans | Human oversight | No (flags for review) |
| Messengers | Context facilitator | No (no vote) |

## Debate Protocol

### Round 1: Opening Statements (parallel)
All agents receive the same `Signal` context and produce independent assessments. ~200 tokens each. No agent sees other agents' opening statements at this stage.

### Round 2: Challenge (sequential)
Agents' Round 1 outputs are shared. Each agent may challenge one other agent's factual claims or reasoning. Challenged agents respond. Messengers resolves factual disputes against the shared `Signal` context.

### Round 3: Synthesis
Athena produces a 400-token synthesis integrating all positions. Each agent then submits a revised probability estimate in `[0.0, 1.0]`.

### Round 4: Vote
Each agent casts `APPROVE / REJECT / ABSTAIN` plus a confidence score. Veto agents (Zeus, Solon) evaluated first — any veto ends deliberation immediately with `REJECTED`. Then weighted majority among remaining agents.

### Output: Thesis
```json
{
  "market_id": "0xabc...",
  "question": "Will X happen by Y?",
  "direction": "YES",
  "council_probability": 0.72,
  "recommended_size_pct": 0.04,
  "edge": 0.12,
  "confidence": 0.81,
  "exit_conditions": {
    "invalidation": "If Z happens, exit immediately",
    "target": 0.88,
    "stop": 0.55,
    "max_hold_days": 14
  },
  "agents": [
    {"agent": "zeus", "vote": "APPROVE", "confidence": 0.75},
    {"agent": "hades", "vote": "APPROVE", "confidence": 0.60},
    ...
  ],
  "trace_id": "trace_abc123",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Swarm vs. Single Agent

The Boule uses a **swarm** architecture: all council agents run in parallel where possible, reducing total deliberation time to ~3x the slowest single agent call. The `swarm.py` module manages parallelism and aggregates results.

The `orchestrator.py` coordinates the four rounds, enforcing timeouts per round. If an agent fails to respond within the timeout, it is marked `ABSTAIN` for that round.

## Memory

Each council agent has access to:
1. Current `Signal` context (market, probability, edge, liquidity)
2. Recent `ScoringRecord` feedback from Ostrakon (their past calibration)
3. Relevant `Lessons` from Underworld (past failures on similar markets)
4. Shared `MarketContext` assembled by Messengers

Memory is managed by `memory/store.py` and `memory/recall.py`. Agents do not share memory across debate rounds — they only share the structured round outputs.

## Trace

Every debate produces a `TraceEvent` stream. See `docs/TRACE_FORMAT.md`.

Traces are archived by Parthenon and viewable in the web UI at `/traces`.

## Configuration

Key params in service config:
- `MIN_QUORUM`: minimum agents that must vote (default: 7)
- `APPROVAL_THRESHOLD`: weighted vote fraction needed (default: 0.60)
- `ROUND_TIMEOUT_SECONDS`: per-round agent timeout (default: 30)
- `MAX_RETRIES`: agent API retry limit (default: 2)
- `BANDS_ELIGIBLE`: which signal bands trigger deliberation (default: S, A)
