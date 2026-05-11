# Argos — Position Monitor

Watches all open positions and manages exits.

## What It Does

1. Subscribes to `strategos:trades` to pick up new open positions
2. Polls each position every 30s for current PnL and probability
3. Triggers exits on target, stop, max hold, invalidation, or emergency
4. Adjusts trailing stops as positions become profitable

## Setup

```bash
cd services/argos
cp .env.example .env
uv run python -m argos
```

## Structure

```
src/argos/
  monitor.py       Main monitoring loop
  pnl.py           PnL calculation
  exits.py         Exit trigger logic
  adjustments.py   Trailing stop logic
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/ARGOS.md` — full service documentation
