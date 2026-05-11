# Ostrakon — Agent Scoring

Scores all council agents after every market resolution.

## What It Does

1. Receives resolution events from Polymarket (via Argos/Strategos)
2. Computes Brier score for each agent's probability estimate
3. Updates Sharpe ratios and calibration curves
4. Rebuilds and publishes the leaderboard
5. Updates ERC-8004 agent reputation on Arc Testnet

## Setup

```bash
cd services/ostrakon
cp .env.example .env
uv run python -m ostrakon
```

## Structure

```
src/ostrakon/
  metrics.py       Metric aggregation pipeline
  brier.py         Brier score computation
  calibration.py   Calibration curve analysis
  sharpe.py        Sharpe ratio computation
  leaderboard.py   Leaderboard construction
  rewards.py       Reward allocation and ERC-8004 updates
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/OSTRAKON.md` — service overview
- `docs/SCORING.md` — full scoring methodology
- `docs/AGENT_PASSPORTS.md` — ERC-8004 integration
