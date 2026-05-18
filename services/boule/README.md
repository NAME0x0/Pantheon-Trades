# Boule — Deliberation Council

Multi-agent AI council that debates every potential trade before execution.

## What It Does

1. Receives S/A band `Signal`s from Apollo
2. Spawns a 13-agent council (each a Claude API call with specialized system prompt)
3. Runs 4-round structured debate: opening → challenge → synthesis → vote
4. Produces a signed `Thesis` with consensus probability, recommended size, and exit conditions
5. Emits full `TraceEvent` stream per deliberation

## Setup

```bash
cd services/boule
cp .env.example .env
# Requires ANTHROPIC_API_KEY
uv run python -m boule.orchestrator
```

## Structure

```
src/boule/
  orchestrator.py       Main pipeline coordinator
  swarm.py              Parallel agent execution
  debate.py             Round-by-round debate logic
  schema.py             Pydantic models (Thesis, ThesisBlock, etc.)
  trace.py              TraceEvent emission
  router.py             Redis stream routing
  agents/
    base.py             Agent base class (Claude API wrapper)
    market_scanner.py   Signal ingestion and queuing
    news_analyst.py     News analysis agent
    sentiment_analyst.py Sentiment analysis agent
    technical_analyst.py Technical chart agent
    bull_researcher.py  Bull case researcher
    bear_researcher.py  Bear case researcher
    risk_manager.py     Risk/downside agent
    execution_agent.py  Execution feasibility agent
    auditor.py          Internal consistency auditor
  memory/
    store.py            Memory storage
    recall.py           Context retrieval for deliberations
  council/
    charter.md          Council operating rules
  prompts/
    base.md             Base system prompt shared by all agents
    zeus.md             Zeus — supreme authority
    hades.md            Hades — risk sovereign
    athena.md           Athena — strategic wisdom
    apollo.md           Apollo — technical analysis
    cassandra.md        Cassandra — tail risk warnings
    ares.md             Ares — bull advocate
    hephaestus.md       Hephaestus — execution mechanics
    solon.md            Solon — compliance
    themis.md           Themis — justice/proportionality
    daedalus.md         Daedalus — structural analysis
    strategos.md        Strategos — execution planning
    humans.md           Humans — oversight proxy
    messengers.md       Messengers — context facilitator
    [role].md           Role-based agent prompts
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/BOULE.md` — full deliberation protocol
- `docs/AGENTS.md` — agent roster and roles
- `docs/TRACE_FORMAT.md` — trace event schema
