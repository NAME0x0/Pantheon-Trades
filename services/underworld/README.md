# Underworld — Failure Analysis

Post-mortem and failure analysis service. Where strategies go to be understood.

## What It Does

1. Archives terminated strategies to the graveyard
2. Runs structured post-mortems on failed theses and strategies
3. Logs agent hallucinations (claims contradicted by data)
4. Catalogs broken assumptions across all post-mortems
5. Extracts lessons and makes them available to Boule memory

## Setup

```bash
cd services/underworld
cp .env.example .env
uv run python -m underworld
```

## Structure

```
src/underworld/
  graveyard.py          Terminated strategy archive
  postmortem.py         Post-mortem analysis
  hallucination_log.py  Agent hallucination tracking
  broken_assumptions.py Assumption failure catalog
  lessons.py            Lesson extraction and retrieval
```

## Triggers

Post-mortems triggered automatically for:
- Thesis with PnL < -30% of capital
- Strategy terminated for performance
- Strategy terminated for drawdown violation

Manual post-mortems can be triggered via Olympus dashboard.

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/UNDERWORLD.md` — full service documentation
