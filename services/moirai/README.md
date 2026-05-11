# Moirai — Strategy Lifecycle

Lifecycle management service. The three Fates control every strategy's existence.

## What It Does

1. **Clotho**: Registers new strategies; validates creation requirements; triggers Elysium backtest
2. **Lachesis**: Assigns strategies to markets; enforces concurrent market limits; manages cooling periods
3. **Atropos**: Terminates strategies; coordinates orderly exit; archives to Underworld
4. **Enforcer**: Validates all state transitions against `docs/MOIRAI_LAWS.md`; blocks invalid transitions

## Setup

```bash
cd services/moirai
cp .env.example .env
uv run python -m moirai
```

## Structure

```
src/moirai/
  laws.py           Lifecycle law definitions
  clotho.py         Strategy creation
  lachesis.py       Strategy assignment
  atropos.py        Strategy termination
  constitution.py   State transition validator
  enforcer.py       Law enforcement against all pipeline events
```

## State Machine

```
DRAFT → REGISTERED → PAPER → LIVE → SUSPENDED → TERMINATED
```

All transitions recorded on `StrategyLifecycle.sol` (Arc Testnet).

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/MOIRAI_LAWS.md` — lifecycle rules
- `docs/STRATEGY_LIFECYCLE.md` — state machine
