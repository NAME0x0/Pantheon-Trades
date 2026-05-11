# Elysium — Simulation

Elysium (Ἠλύσιον) was the paradise afterlife for heroes — where the great could relive their adventures eternally. In Pantheon Trades, Elysium is the simulation and backtesting environment where strategies are tested before live deployment and replayed after resolution.

## Components

`services/elysium/`:

### `backtest.py` — Historical Backtesting
Replays a strategy against historical Polymarket data:
- Simulates Apollo signal generation on historical market snapshots
- Runs Boule deliberations on those signals (using real LLM calls)
- Applies Areopagus risk gates with the current policy
- Simulates fills at historical mid-prices
- Computes actual PnL based on resolution outcomes

A full backtest run takes ~30-60 minutes for 30 days of history (due to LLM call costs).

### `simulator.py` — Scenario Simulation
Runs synthetic market scenarios without historical data:
- Define a market scenario (starting probability, resolution date, expected catalysts)
- Simulate how Apollo and Boule would respond
- Useful for testing edge cases (thin markets, extreme sentiment, etc.)

### `counterfactual.py` — Counterfactual Oracle
For each resolved market with a ProofOfRestraint:
- Computes hypothetical PnL if trade had been executed
- Submits result to `NoTradeAlpha.sol`
- See `docs/COUNTERFACTUAL.md`

### `replay.py` — Deliberation Replay
Replays a specific historical deliberation with different parameters:
```bash
uv run python -m elysium.replay --thesis-id abc123 --new-policy risk_policy_v2.json
```
Produces comparison trace: original vs. replayed.

### `paper_arena.py` — Paper Trading
Runs live deliberations in shadow mode — same pipeline as live but no real orders submitted. Tracks paper positions in PostgreSQL.

Used for:
- New strategy evaluation (required before live promotion)
- Testing prompt updates without risk
- Ongoing parallel shadow of live system

### `overfit_detector.py` — Overfitting Detection
Compares backtest performance vs. live/paper performance. Flags strategies where backtest significantly outperforms live:

```python
overfit_score = (backtest_sharpe - live_sharpe) / backtest_sharpe
# overfit_score > 0.5 = potentially overfit
```

Also runs walk-forward analysis: tests strategy on periods not used in initial backtest.

## Promotion Gate

Before any strategy can be promoted from paper to live, Elysium must:
1. Complete a 30-day backtest with `status = PASS`
2. Run overfit detector (must not flag as overfit)
3. Run paper arena for minimum 10 paper trades
4. All results archived to Parthenon

Results available in Olympus promotion review panel.

## Service CLI

```bash
# Run backtest for a strategy
cd services/elysium && uv run python -m elysium.backtest --strategy my_strategy --days 30

# Run paper arena
cd services/elysium && uv run python -m elysium.paper_arena --strategy my_strategy

# Run counterfactuals for resolved markets
cd services/elysium && uv run python -m elysium.counterfactual --date 2024-01-15
```
