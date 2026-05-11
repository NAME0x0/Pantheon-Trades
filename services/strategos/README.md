# Strategos — Execution Service

Routes approved theses to execution on the Polymarket CLOB.

## What It Does

1. Receives `ApprovalToken` from Areopagus
2. Estimates slippage from orderbook depth
3. Submits limit orders to Polymarket CLOB (live) or paper executor (paper mode)
4. Tracks order fills and emits `Trade` events
5. Routes `ExitSignal` from Argos to close positions

## Setup

```bash
cd services/strategos
cp .env.example .env
# Requires POLYMARKET_API_KEY
uv run python -m strategos
```

## Structure

```
src/strategos/
  router.py           Execution router (live vs. paper)
  live.py             Live CLOB executor
  paper.py            Paper trade executor
  orderbook.py        Orderbook utilities
  slippage.py         Slippage estimation
  latency.py          Latency tracking
  polymarket_clob.py  Polymarket CLOB API client
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/STRATEGOS.md` — full service documentation
- `docs/POLYMARKET_NOTES.md` — CLOB integration details
- `docs/LATENCY_BUDGET.md` — timing constraints
