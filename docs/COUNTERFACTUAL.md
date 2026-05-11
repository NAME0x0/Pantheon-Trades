# Counterfactual Analysis

Elysium's counterfactual module answers: *what would have happened if we had made a different decision?*

## Two Modes

### Mode 1: No-Trade Counterfactual
For every ProofOfRestraint, after market resolution:
- Compute hypothetical PnL if the trade had been executed at the signal price
- Record to `NoTradeAlpha.sol`
- Surfaces whether restraint was correct

### Mode 2: Thesis Validation Counterfactual
For every executed trade, after market resolution:
- Was the actual outcome within the range the thesis predicted?
- Which agents' probability estimates were most accurate?
- What did Cassandra warn about that actually materialized?

## Counterfactual Oracle

`CounterfactualOracle.sol` stores both types of counterfactual data:

```solidity
struct CounterfactualResult {
    bytes32 referenceId;    // restraintId or thesisId
    ResultType resultType;  // NO_TRADE or THESIS_VALIDATION
    uint256 resolutionValue;
    int256 hypotheticalPnl;
    bytes32[] accurateAgents;  // agents whose estimates were within 10% of actual
    bytes32[] inaccurateAgents;
    uint256 timestamp;
}
```

## Counterfactual Runner (Elysium)

`counterfactual.py` runs automatically after every market resolution:

```python
async def run_counterfactual(market_id: str, resolution_value: float):
    # Find all restraints for this market
    restraints = await db.get_restraints(market_id=market_id)
    for restraint in restraints:
        pnl = compute_hypothetical_pnl(restraint, resolution_value)
        await oracle.record(restraint.restraint_id, ResultType.NO_TRADE, pnl)
    
    # Find all executed theses for this market
    theses = await db.get_theses(market_id=market_id, status="executed")
    for thesis in theses:
        agent_accuracy = compute_agent_accuracy(thesis, resolution_value)
        await oracle.record(thesis.thesis_id, ResultType.THESIS_VALIDATION, agent_accuracy)
```

## Agent Accuracy

For each agent's probability estimate vs. actual resolution:

```
agent_error = abs(agent.probability_estimate - resolution_value)
```

- Error ≤ 0.10: agent is "accurate" for this market
- Error > 0.30: agent is "significantly off"
- Error > 0.50: agent was confidently wrong

Accuracy tracked per agent, per category (crypto/politics/etc.), per market type. Fed back to Ostrakon for Brier scoring.

## Counterfactual Suppression Prevention

Per Constitution Article IX, Elysium must run counterfactuals for ALL resolved markets that had S/A signals, including those where the system was wildly wrong. There is no mechanism to suppress unflattering counterfactuals — they are written directly to `CounterfactualOracle.sol` by Parthenon and cannot be deleted.

## Replay

Elysium can replay any historical deliberation with updated parameters:

```bash
cd services/elysium && uv run python -m elysium.replay --thesis-id abc123 --new-config risk_policy_v2.json
```

This re-runs the Boule deliberation with historical data and the new config, producing a comparison trace showing how the outcome would have differed.

Useful for:
- Evaluating proposed risk policy changes before applying them
- Post-mortem: "would a stricter edge threshold have prevented this loss?"
- Tuning agent prompt updates against historical data
