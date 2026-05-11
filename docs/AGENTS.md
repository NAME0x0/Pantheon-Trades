# Agents

## Overview

Pantheon Trades uses two categories of agents:

1. **Council Agents** — AI personas inside the Boule deliberation system, each playing a specific epistemic role in thesis debates
2. **Service Agents** — autonomous Python services that perform specific pipeline functions

## Council Agents (Boule)

Each council agent is a Claude API invocation with a specialized system prompt. Agents debate in structured rounds and produce signed `ThesisBlock` outputs.

### Zeus — Supreme Authority
- **Role**: Final veto and constitutional guardian
- **Domain**: Whether the trade violates core principles or system constitution
- **Vote weight**: Veto power (single Zeus rejection = thesis rejected)
- **Prompt**: `services/boule/src/boule/prompts/zeus.md`

### Hades — Risk Sovereign
- **Role**: Worst-case and downside analysis
- **Domain**: What is the maximum plausible loss? What black swans apply?
- **Vote weight**: 2x on risk-related dimensions
- **Prompt**: `services/boule/src/boule/prompts/hades.md`

### Athena — Strategic Wisdom
- **Role**: Quality of reasoning and logical consistency
- **Domain**: Is the thesis internally coherent? Are the assumptions valid?
- **Vote weight**: 1.5x on reasoning quality
- **Prompt**: `services/boule/src/boule/prompts/athena.md`

### Apollo — Technical Oracle
- **Role**: Price action and chart analysis
- **Domain**: Trend, support/resistance, volume, momentum signals
- **Vote weight**: 1x
- **Prompt**: `services/boule/src/boule/prompts/apollo.md`

### Cassandra — Prophetic Warning
- **Role**: Tail risks, ignored warnings, adverse scenarios
- **Domain**: What are the low-probability catastrophic outcomes? What is the market missing?
- **Vote weight**: 1x (but any Cassandra warning triggers mandatory Areopagus secondary review)
- **Prompt**: `services/boule/src/boule/prompts/cassandra.md`

### Ares — Bull Advocate
- **Role**: Aggressive upside case
- **Domain**: Maximum momentum, positive catalysts, why this resolves YES
- **Vote weight**: 1x
- **Prompt**: `services/boule/src/boule/prompts/ares.md`

### Hephaestus — Execution Mechanic
- **Role**: Feasibility of execution
- **Domain**: Slippage, liquidity depth, timing, fill probability
- **Vote weight**: 1x; Hephaestus rejection = thesis flagged for manual review
- **Prompt**: `services/boule/src/boule/prompts/hephaestus.md`

### Solon — Lawgiver
- **Role**: Rules compliance and policy adherence
- **Domain**: Does the thesis comply with risk policy, Moirai laws, and constitution?
- **Vote weight**: Compliance veto (policy violation = immediate rejection)
- **Prompt**: `services/boule/src/boule/prompts/solon.md`

### Themis — Justice
- **Role**: Fairness, proportionality, systemic risk
- **Domain**: Is the position size proportional to edge? Does this create systemic bias?
- **Vote weight**: 1x
- **Prompt**: `services/boule/src/boule/prompts/themis.md`

### Daedalus — Structural Analyst
- **Role**: Complexity and structural risk
- **Domain**: Is the strategy too complex? Hidden dependencies? Second-order effects?
- **Vote weight**: 1x
- **Prompt**: `services/boule/src/boule/prompts/daedalus.md`

### Strategos — Execution Planner
- **Role**: Operational execution planning
- **Domain**: Sequence of orders, timing, partial fill handling
- **Vote weight**: 1x (advisory only — actual execution done by Strategos service)
- **Prompt**: `services/boule/src/boule/prompts/strategos.md`

### Humans — Human Oversight
- **Role**: Human-in-the-loop representation
- **Domain**: Would a reasonable human approve this? Flag for human review if uncertain
- **Vote weight**: 1x; Humans flag triggers human review queue
- **Prompt**: `services/boule/src/boule/prompts/humans.md`

### Messengers — Communication Layer
- **Role**: Inter-agent communication and context relay
- **Domain**: Ensures all agents have shared context; prevents hallucinated premises
- **Vote weight**: 0 (facilitator role only)
- **Prompt**: `services/boule/src/boule/prompts/messengers.md`

## Debate Structure

```
Round 1 — Opening Statements
  Each agent produces initial assessment (~200 tokens)

Round 2 — Challenge
  Each agent may challenge 1-2 other agents' claims
  Challenged agent must respond

Round 3 — Synthesis
  Athena produces a synthesis of the debate
  Each agent updates their probability estimate

Round 4 — Vote
  Each agent casts: APPROVE / REJECT / ABSTAIN + confidence %
  Zeus and Solon can veto (immediate rejection)
  Simple majority + weighted confidence for approval

Output
  Thesis: consensus probability, recommended size, exit conditions
  Trace: full debate transcript per agent
```

## Voting Rules

- **Veto agents**: Zeus (constitutional), Solon (compliance) — single veto rejects
- **Majority**: ≥60% weighted vote required for approval
- **Minimum quorum**: 7 of 12 voting agents must participate
- **Cassandra flag**: any tail risk flag requires Areopagus secondary review even on approval

## Service Agents

These are autonomous Python services, not LLM-based:

| Agent | Service | Role |
|-------|---------|------|
| Signal Generator | Apollo | Market opportunity detection |
| Risk Gate | Areopagus | Pre-trade risk enforcement |
| Executor | Strategos | CLOB order submission |
| Monitor | Argos | Position watching and exit logic |
| Scorer | Ostrakon | Calibration and leaderboard |
| Archivist | Parthenon | Permanent storage and proofs |
| Oracle | Pythia | Data ingestion |
| Simulator | Elysium | Backtesting and paper trading |
| Coroner | Underworld | Post-mortem analysis |
| Lawgiver | Moirai | Lifecycle enforcement |
| Governor | Olympus | System orchestration |

## Agent Scoring

All council agents accumulate performance records via Ostrakon:
- **Brier score**: calibration of probability estimates (lower is better; 0.33 = random)
- **Sharpe**: risk-adjusted return on recommendations
- **Credibility weight**: fed back to Boule as debate influence modifier

Agents with Brier score > 0.33 or sustained negative Sharpe trigger Olympus review for demotion or exile.

See `docs/SCORING.md` and `docs/AGENT_PASSPORTS.md`.
