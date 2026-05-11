# Elysium — Simulation

Backtesting, paper trading, and counterfactual analysis service.

## What It Does

1. Backtests strategies against historical Polymarket data
2. Runs paper trading arena (shadow mode, no real capital)
3. Computes counterfactual PnL for ProofOfRestraint decisions
4. Replays historical deliberations with new parameters
5. Detects overfitting in strategy performance

## Setup

```bash
cd services/elysium
cp .env.example .env
uv run python -m elysium
```

## Structure

```
src/elysium/
  backtest.py          Historical backtesting
  simulator.py         Scenario simulation
  counterfactual.py    Counterfactual oracle
  replay.py            Deliberation replay
  paper_arena.py       Paper trading mode
  overfit_detector.py  Overfitting detection
```

## Usage

```bash
# Backtest a strategy
uv run python -m elysium.backtest --strategy strategy_name --days 30

# Run counterfactuals for a date
uv run python -m elysium.counterfactual --date 2024-01-15

# Replay a specific deliberation
uv run python -m elysium.replay --thesis-id abc123
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/ELYSIUM.md` — full service documentation
- `docs/COUNTERFACTUAL.md` — counterfactual methodology
- `docs/NO_TRADE_ALPHA.md` — no-trade alpha calculation
