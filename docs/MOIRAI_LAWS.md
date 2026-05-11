# Moirai Laws — Strategy Lifecycle

The Moirai (Μοῖραι, "Fates") are the three sisters who control the destiny of every mortal: Clotho spins the thread of life, Lachesis measures it, and Atropos cuts it. In Pantheon Trades, Moirai enforces the lifecycle of every trading strategy.

## The Three Fates

### Clotho — Creation
Clotho handles strategy birth. No strategy enters the system without Clotho registration.

**Creation requirements:**
1. Strategy has a valid name and description
2. Strategy is assigned to at least one target market category
3. Strategy has defined entry conditions (minimum band, minimum edge)
4. Strategy has defined exit conditions (target, stop, max_hold_days)
5. Strategy is assigned a capital allocation from the GoalsBoard budget
6. Elysium has run a minimum 30-day backtest and the result is archived

**On creation**: `StrategyLifecycle.sol` records `CREATED` state on-chain.

### Lachesis — Assignment
Lachesis manages the active life of a strategy — assigning it to markets, threading it through the Boule pipeline, and monitoring its fate.

**Assignment rules:**
1. A strategy may be assigned to at most `MAX_CONCURRENT_MARKETS` markets simultaneously (default: 5)
2. Assignment to a new market requires a fresh Signal of the required band
3. Re-assignment after a failed thesis requires a 24h cooling period
4. A strategy running in paper mode must complete at least 10 paper trades before live assignment

**On assignment**: `StrategyLifecycle.sol` records `ASSIGNED` state with market ID.

### Atropos — Termination
Atropos terminates strategies. Termination is irreversible.

**Termination triggers:**
1. **Voluntary**: Operator submits termination request; 24h graceful shutdown
2. **Performance**: Ostrakon Brier score > 0.33 for 30 consecutive days → automatic exile proposal
3. **Drawdown**: Strategy-level drawdown exceeds `STRATEGY_DRAWDOWN_LIMIT` (default: 20%)
4. **Olympus exile**: Governance votes to exile the strategy
5. **Constitutional violation**: Zeus or Solon veto on >50% of deliberations in a 7-day window

**On termination**: 
- Open positions handed to Argos for orderly exit
- Strategy archived to Underworld for post-mortem
- `StrategyLifecycle.sol` records `TERMINATED` state
- Elysium computes full counterfactual retrospective

## Strategy States

```
DRAFT ──► REGISTERED ──► PAPER ──► LIVE ──► SUSPENDED ──► TERMINATED
              │                              │
              └──────────────────────────────┘ (exile shortcut)
```

- **DRAFT**: Created locally, not yet submitted to Moirai
- **REGISTERED**: Clotho accepted; Elysium backtest running
- **PAPER**: Running in Elysium paper arena; no live capital
- **LIVE**: Active; Lachesis assigning to markets
- **SUSPENDED**: Temporarily paused (e.g., drawdown pause); can resume
- **TERMINATED**: Permanently ended by Atropos; cannot restart

## Promotion: Paper → Live

A strategy must meet all of the following to be promoted from paper to live:

| Criterion | Threshold |
|-----------|-----------|
| Minimum paper trades | 10 |
| Paper Brier score | < 0.25 |
| Paper Sharpe ratio | > 0.5 |
| Win rate (profitable resolutions) | > 45% |
| Elysium overfit check | PASS |
| Human review | Approved |

Promotion proposal submitted to Olympus. Olympus approves or rejects within 48h.

## Cooling Periods

| Event | Cooling Period |
|-------|---------------|
| Failed thesis on a market | 24h before re-entry on same market |
| Strategy-level drawdown > 10% | 48h before new entries |
| Thesis rejection rate > 60% in 24h | 12h before new deliberations |
| Areopagus secondary review triggered | Until review completes |

## Enforcement

Moirai runs as an independent service. It checks strategy state before every Boule deliberation. If a strategy is in an invalid state (suspended, terminated, cooling), it blocks the pipeline.

The `constitution.py` module verifies every state transition against these laws before writing to `StrategyLifecycle.sol`.
