# Proof of Restraint

Proof of Restraint is the mechanism by which Pantheon Trades records and proves that it chose *not* to trade on a valid signal.

## Why It Matters

A trading system that only records trades can be evaluated on its wins. A system that also records its non-trades can be evaluated on its judgment. Proof of Restraint makes every no-trade decision a first-class, verifiable, permanent record.

Benefits:
1. **Accountability**: Cannot cherry-pick results by hiding failed non-trades
2. **Calibration**: Counterfactual analysis (via `NoTradeAlpha`) shows whether restraint was correct
3. **Trust**: External auditors can verify the system is not over-trading
4. **Constitution compliance**: Article III mandates every S/A no-trade is recorded

## When Proof of Restraint is Issued

Any signal that reaches band **S or A** that does not result in an executed trade:

| Trigger | Reason |
|---------|--------|
| Zeus veto | Constitutional violation |
| Solon veto | Policy compliance violation |
| Areopagus rejection | Risk gate failure |
| Areopagus resize → sub-threshold | Position too small after Kelly |
| Deliberation timeout | Boule did not complete within time budget |
| Signal expiry | Signal TTL exceeded before execution |
| Manual operator rejection | Human override |

Band B, C, D signals do not generate ProofOfRestraint — they are filtered before reaching Boule.

## On-Chain Record

`ProofOfRestraint.sol`:

```solidity
struct Restraint {
    bytes32 restraintId;    // uuid
    bytes32 signalHash;     // Hash of the Signal
    bytes32 thesisHash;     // Hash of the Thesis (if deliberation completed)
    bytes32 rejectionReason;// Enum: ZEUS_VETO, SOLON_VETO, RISK_GATE, etc.
    uint256 signalEdge;     // Scaled 1e4 (e.g., 1200 = 12% edge)
    uint256 signalBand;     // 1=S, 2=A
    uint256 timestamp;
    bool counterfactualSet; // true after market resolves
}
```

## Counterfactual Resolution

After the market resolves, `NoTradeAlpha.sol` records what would have happened:

```solidity
function resolveCounterfactual(
    bytes32 restraintId,
    uint256 resolutionValue,   // 1e18 or 0
    int256 hypotheticalPnl,    // positive = good not to trade (dodged a loss)
                               // negative = missed a profitable trade
    bytes calldata oracleProof
) external
```

This is computed by Elysium's `counterfactual.py` and submitted by Parthenon.

## No-Trade Alpha Dashboard

The web UI `/leaderboard` includes a "Restraint Quality" section:

| Metric | Description |
|--------|-------------|
| Total restraints | Count of ProofOfRestraint records |
| Good restraints | Restraints where `hypotheticalPnl < 0` (correctly avoided losses) |
| Costly restraints | Restraints where `hypotheticalPnl > 0` (missed profitable trades) |
| Restraint quality | `good_restraints / total_restraints` |
| Avg. missed PnL | Average hypothetical PnL on costly restraints |

Target restraint quality: > 50% (more than half of no-trades were correct).

## Service Flow

```
Signal (band S/A) → Boule (or skip if veto before deliberation)
                                │
                    No trade decision
                                │
                                ▼
                   Areopagus calls Parthenon:
                   issue_restraint(signal, thesis, reason)
                                │
                                ▼
                   Parthenon archives signal + thesis to IPFS
                                │
                                ▼
                   Parthenon calls ProofOfRestraint.sol
                   records restraintId on-chain
                                │
                    [Market resolves later]
                                │
                                ▼
                   Elysium computes hypotheticalPnl
                                │
                                ▼
                   Parthenon calls NoTradeAlpha.resolveCounterfactual()
```
