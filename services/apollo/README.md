# Apollo — Signal Engine

Generates and scores trading signals from Polymarket market data.

## What It Does

1. Receives `MarketSnapshot` data from Pythia
2. Scores each market across 6 feature dimensions (edge, liquidity, volatility, catalyst, sentiment, correlation)
3. Classifies markets into signal bands (S, A, B, C, D)
4. Publishes S/A band signals to `apollo:signals` Redis stream

## Setup

```bash
cd services/apollo
cp .env.example .env
uv run python -m apollo.cli run --interval 60
```

## Structure

```
src/apollo/
  bands.py          Band classification and management
  filters.py        Pre-scoring market filters
  scorer.py         Main scoring orchestrator
  runner.py         Continuous scan loop
  cli.py            CLI entry point
  features/
    edge.py         Probability mispricing score
    liquidity.py    Orderbook depth score
    volatility.py   Volatility regime score
    catalyst.py     Catalyst proximity score
    sentiment.py    Aggregated sentiment score
    correlation.py  Portfolio independence score
    trend.py        Price trend alignment score
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/APOLLO.md` — full service documentation
- `docs/SIGNAL_SPEC.md` — signal schema and band thresholds
