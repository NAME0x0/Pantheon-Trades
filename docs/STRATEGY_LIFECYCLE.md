# Strategy Lifecycle

See `docs/MOIRAI_LAWS.md` for the governing rules.

## States

```
DRAFT → REGISTERED → PAPER → LIVE → SUSPENDED → TERMINATED
```

### DRAFT
Local only. Not yet submitted to Moirai. No pipeline execution.

### REGISTERED
Submitted to Moirai (Clotho). Elysium backtest running.

Required for registration:
- Name, description, target categories
- Entry conditions (min band, min edge, min confidence)
- Exit conditions (target, stop, max_hold_days)
- Capital allocation from GoalsBoard budget
- Minimum Elysium backtest: 30 days

### PAPER
Promoted from REGISTERED after backtest passes.

Pipeline runs identically to live but Strategos routes to paper executor. All deliberations, theses, and "trades" are tracked in paper mode.

Minimum paper run before live promotion: 10 paper trades.

### LIVE
Promoted from PAPER after promotion criteria met (see `docs/MOIRAI_LAWS.md`).

Full pipeline active. Real USDC on the line.

### SUSPENDED
Temporary halt. Entry: drawdown pause, service degradation, operator action.

Open positions continue to be managed. No new entries.

Exit to LIVE: drawdown resets or issue resolved. Requires Olympus confirmation.

### TERMINATED
Permanent end. Atropos cuts the thread.

On termination:
1. Open positions exited by Argos (orderly close, not emergency)
2. Final PnL snapshot taken
3. All artifacts archived to Parthenon
4. Strategy record added to `Underworld.graveyard`
5. Post-mortem triggered if terminated for performance reasons
6. `StrategyLifecycle.sol` records TERMINATED state

Cannot restart a terminated strategy. Create a new strategy (Clotho) if the same approach is desired.

## On-Chain Contract

`StrategyLifecycle.sol`:
```solidity
mapping(bytes32 => StrategyState) public states;

function transition(
    bytes32 strategyId,
    State newState,
    bytes32 reason
) external;

event StateTransitioned(
    bytes32 indexed strategyId,
    State from,
    State to,
    bytes32 reason,
    uint256 timestamp
);
```

Every transition is permanently recorded and publicly queryable.

## Multiple Strategies

The system supports multiple concurrent strategies, each in its own lifecycle state.

Constraints:
- Total live capital across all strategies: limited by portfolio exposure limits
- Concurrent markets per strategy: max 5 (Lachesis limit)
- Paper and live strategies can run simultaneously

## Promotion Review

Promotion from paper to live requires human review:
1. Olympus creates a promotion review item in the web UI
2. Operator reviews Elysium metrics, overfitting report, and paper trade history
3. Operator approves or rejects
4. On approval: Moirai transitions to LIVE state, records on-chain
