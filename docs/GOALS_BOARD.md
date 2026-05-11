# Goals Board

The Goals Board tracks system-level performance objectives. Managed by Olympus, displayed on the web UI dashboard.

## Goals

### Daily Bread
**Type**: Daily reset
**Goal**: Complete at least 1 Boule deliberation per day (paper or live)
**Metric**: `deliberation_count_today`
**Why**: Ensures the pipeline is exercised daily; catches silent failures

### Odyssey
**Type**: Cumulative
**Goal**: Reach 100 live trades closed (the journey, not the destination)
**Metric**: `live_trades_closed_total`
**Why**: Milestone tracking for system maturity

### Oracle Watch
**Type**: Continuous
**Goal**: All critical data sources fresh within last 5 minutes
**Metric**: `max_source_staleness_seconds`
**Why**: Data quality is the foundation of signal quality

### War Room
**Type**: Rolling 7-day
**Goal**: Weekly drawdown < 5%
**Metric**: `weekly_drawdown_pct`
**Why**: Drawdown discipline; flag if risk management is slipping

### Forbidden Markets
**Type**: Continuous
**Goal**: Zero trades in blacklisted market categories
**Metric**: `forbidden_market_trade_count`
**Blacklist**: [to be configured per deployment]
**Why**: Legal and ethical guardrails

### Calibration Quest
**Type**: Rolling 30-day
**Goal**: Average council agent Brier score < 0.25
**Metric**: `avg_council_brier_30d`
**Why**: Tracks whether agents are improving or degrading in calibration

### Paper-to-Live Pipeline
**Type**: Milestone
**Goal**: At least 1 strategy in LIVE state
**Metric**: `live_strategy_count`
**Why**: Ensures the promotion pipeline is functional

## On-Chain Recording

Goal completions are recorded on `GoalsBoard.sol`:

```solidity
event GoalCompleted(
    bytes32 indexed goalId,
    string goalName,
    uint256 timestamp,
    bytes32 evidenceHash  // IPFS CID of metrics snapshot
);
```

## Dashboard

Web UI home dashboard shows goals board:
- Progress bars for cumulative/milestone goals
- Status badges for continuous goals
- Historical completion timeline

Goals reset and archive to history at their respective intervals.
