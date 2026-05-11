# Risk Policy

All position sizing and risk limits are enforced by the Areopagus service. This document is the authoritative source. Changes require ZeusMultisig approval (3/5 signers).

## Position Limits

### Per-Trade Limits

| Parameter | Default | Hard Limit |
|-----------|---------|------------|
| Max position size (% of portfolio) | 5% | 10% |
| Min edge required | 0.05 | — |
| Min council confidence | 0.65 | — |
| Min liquidity score | 0.50 | — |
| Max spread | 0.08 | 0.12 |
| Min days to resolution | 2 | 1 |
| Max days to resolution | 90 | 180 |
| Max staleness (seconds) | 300 | 600 |

### Portfolio Limits

| Parameter | Default | Hard Limit |
|-----------|---------|------------|
| Max open positions | 10 | 20 |
| Max total exposure (% of portfolio) | 40% | 60% |
| Max exposure per category | 15% | 25% |
| Max correlated exposure (same underlying) | 10% | 15% |
| Max daily VaR (95%) | 8% | 15% |

### Drawdown Limits

| Trigger | Action |
|---------|--------|
| Daily drawdown > 3% | Pause new entries for 24h |
| Daily drawdown > 5% | Pause all new entries; Olympus notified |
| Weekly drawdown > 8% | Emergency pause; human review required |
| Max peak-to-trough drawdown > 15% | System halt; ZeusMultisig required to resume |

## Kelly Criterion

Areopagus applies Kelly criterion for position sizing:

```
full_kelly = edge / (1 - market_probability + edge)
half_kelly = full_kelly * 0.5
```

The system uses **half-Kelly** by default. Full Kelly is never used.

If `half_kelly > max_position_pct`, the position is resized to `max_position_pct`.

If `half_kelly < min_position_threshold` (0.005 = 0.5%), the thesis is rejected as sub-threshold.

## Invalidation Gates

Areopagus rejects a thesis if any of the following are true:

1. **Staleness**: Any data source older than `max_staleness_seconds`
2. **Spread breach**: Market spread > `max_spread`
3. **Liquidity collapse**: `liquidity_score < min_liquidity_score`
4. **Drawdown triggered**: Active drawdown pause in effect
5. **Exposure breach**: Adding this position would exceed portfolio limits
6. **Correlation breach**: Position too correlated with existing open positions
7. **Solon veto**: Compliance violation flagged during Boule
8. **Zeus veto**: Constitutional violation flagged during Boule
9. **Cassandra flag + secondary review pending**: Cannot proceed until Areopagus secondary review clears

## Conflict of Interest

Areopagus checks for "conflict of interest" — if the system has an existing position in the same market, a thesis for the opposite direction is automatically flagged for human review before proceeding.

## Emergency Pause

The `EmergencyPause` contract and the Olympus service can halt all new trade entries instantly. Open positions continue to be managed by Argos.

Manual resume requires ZeusMultisig (3/5 signers). See `docs/EMERGENCY_PAUSE.md`.

## Audit Trail

Every Areopagus decision is logged with:
- Thesis ID
- Decision: APPROVED / REJECTED / RESIZED
- Reason code
- Final position size
- Active limits at time of decision
- Timestamp

All decisions are archived by Parthenon and anchored on-chain.

## Changing This Policy

Policy changes require:
1. Proposal submitted to ZeusMultisig
2. 72-hour timelock
3. 3/5 multisig signers approve
4. Updated `RISK_POLICY.md` committed to main branch
5. Areopagus service config updated

See `docs/ZEUS_MULTISIG.md`.
