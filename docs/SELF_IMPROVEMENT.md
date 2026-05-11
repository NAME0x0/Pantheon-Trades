# Self-Improvement

Pantheon Trades includes mechanisms for the system to improve its own performance over time through structured feedback loops.

## Feedback Loops

### Loop 1: Ostrakon → Boule (Credibility Weights)

After every market resolution:
1. Ostrakon updates each agent's Brier score and Sharpe ratio
2. Credibility weights recomputed and published to `ostrakon:weights`
3. Boule's next deliberation uses updated weights

Effect: Agents with good calibration get more influence in future deliberations. Poorly calibrated agents are progressively downweighted before eventually being exiled.

### Loop 2: Underworld → Boule (Lessons)

When Underworld completes a post-mortem:
1. Lessons extracted from failed thesis analysis
2. Lessons stored in Boule's memory store
3. Future deliberations on similar market types include relevant lessons in agent context

Effect: Agents "learn" from past failures by having failed assumptions available as context.

### Loop 3: Elysium → Areopagus (Policy Tuning)

Monthly:
1. Elysium analyzes No-Trade Alpha and win rate across all strategies
2. If No-Trade Alpha is systematically negative (too many missed good trades), report to Olympus
3. Olympus generates a policy review recommendation
4. ZeusMultisig votes on threshold adjustments

Effect: Risk policy adapts to observed market conditions over time.

### Loop 4: Elysium → Agent Prompts (A/B Testing)

When a prompt update is proposed:
1. Elysium runs a 30-day historical backtest comparing old vs. new prompt
2. Metrics: Brier score, Sharpe, vote consistency, deliberation quality
3. If new prompt outperforms on 2+ metrics with no regression on others: flagged for approval
4. ZeusMultisig approves minor or major update

Effect: Agent prompts can be empirically improved against historical outcomes.

### Loop 5: Adversarial Mode → Security (Robustness)

Monthly:
1. Olympus activates adversarial mode for 24h
2. Adversary agents attempt to manipulate Boule outcomes
3. Results analyzed: which manipulation attempts succeeded?
4. Targeted hardening applied to vulnerable agents or Messengers filtering

See `docs/ADVERSARIAL_MODE.md`.

## Limits on Self-Improvement

Per Constitution Article II and Article X:
- No self-improvement can reduce Zeus or Solon's veto power
- No self-improvement can eliminate Humans agent participation
- No self-improvement can suppress Cassandra flags
- All prompt changes require ZeusMultisig approval — the system cannot unilaterally modify its own core agent behaviors

The system can improve within its constitutional constraints, but cannot rewrite its own constitution.
