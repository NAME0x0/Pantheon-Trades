# Scoring — Ostrakon

Ostrakon (ὄστρακον, "potsherd") is the system by which ancient Athenians voted to exile citizens. In Pantheon Trades, Ostrakon scores every council agent and surfaces poor performers for exile.

## Metrics

### Brier Score
Measures calibration of probability estimates. Lower is better.

```
brier_score = (probability_estimate - actual_outcome)²
```

Where `actual_outcome` = 1.0 (resolved YES) or 0.0 (resolved NO).

- **Perfect calibration**: 0.00
- **Random guessing**: 0.25
- **Maximum error**: 1.00
- **Exile threshold**: > 0.33 for 30 consecutive resolved theses

### Sharpe Ratio
Risk-adjusted return on the agent's recommendations.

```
sharpe = (mean_pnl_contribution - risk_free_rate) / std_pnl_contribution
```

Where `pnl_contribution` is the attributed PnL for positions where the agent voted APPROVE.

Rolling window: 30 days. Minimum 10 observations to compute.

- **Target**: > 1.0
- **Acceptable**: > 0.5
- **Review threshold**: < 0.0 for 7+ days
- **Exile threshold**: < -0.5 for 30 days

### Calibration Score
Measures whether stated confidence is accurate. Computed via calibration curve binning.

```
calibration_error = sum(|bin_average_confidence - bin_accuracy|) / num_bins
```

Well-calibrated agent: says 70% confidence → correct ~70% of the time.

### Vote Consistency
Tracks whether an agent's vote aligns with their stated probability:
- Agent says p=0.8 then votes REJECT → flagged as inconsistency
- Persistent inconsistency (>20% rate) → flagged to Olympus

### Veto Quality (Zeus/Solon only)
For veto agents, tracks the quality of veto decisions:
- Veto upheld by retrospective = good veto
- Vetoed thesis would have been profitable = bad veto (costly restraint)
- Veto rate: flags if < 5% or > 30% of eligible theses

## Leaderboard

Updated after every market resolution. Published to:
- Web UI: `/leaderboard`
- Redis: `ostrakon:leaderboard` stream
- On-chain: `AgentReputation.sol`

Leaderboard fields per agent:
```
rank, agent_name, brier_score_30d, sharpe_30d, total_theses,
win_rate, calibration_error, credibility_weight, status
```

## Credibility Weight

Each agent's credibility weight is fed back to Boule to modulate vote influence.

```
credibility_weight = base_weight * calibration_multiplier * sharpe_multiplier
```

Where:
- `calibration_multiplier` = `max(0.5, 1.0 - calibration_error * 2)`
- `sharpe_multiplier` = `max(0.5, min(2.0, 1.0 + sharpe_30d * 0.5))`

Minimum credibility: 0.25 (agent still participates but with reduced influence).
Maximum credibility: 2.5 (top-performing agents get extra weight).

## Rewards

Ostrakon computes performance-based reward allocations for:
- Agent identity contracts (ERC-8004 reputation updates)
- Future capital allocation proportional to performance

Rewards are tracked in `rewards.py` and recorded on `AgentReputation.sol`.

## Exile Process

When an agent hits an exile threshold:
1. Ostrakon emits `exile_proposal` to `ostrakon:proposals` stream
2. Olympus receives proposal, creates a review item
3. Human operators review within 48h
4. If confirmed: Moirai/Atropos terminates the agent's strategy assignment
5. Agent passport updated with `EXILED` status on `AgentPassport.sol`
6. Underworld runs post-mortem on the agent's history

See `docs/UNDERWORLD.md` and `docs/ADVERSARIAL_MODE.md`.
