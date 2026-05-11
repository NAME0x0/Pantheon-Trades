# No-Trade Alpha

No-Trade Alpha is the quantified value of *not* trading. The `NoTradeAlpha` contract and Elysium module measure whether the system's restraint decisions add or destroy value.

## Concept

In prediction markets, the cost of a bad trade is symmetric with the cost of a missed good trade — but they are not equivalent. Bad trades consume capital and generate losses. Missed good trades generate opportunity cost but do not directly harm the portfolio. However, systematic over-restraint destroys expected value just as systematic over-trading destroys capital.

No-Trade Alpha answers: **Is our judgment about when not to trade correct?**

## Calculation

For each `ProofOfRestraint`:

```
hypothetical_entry_price = signal.market_probability   # price at time of restraint
hypothetical_exit_price  = resolution_value            # 1.0 (YES) or 0.0 (NO)
hypothetical_size_usdc   = areopagus.final_size_usdc   # what would have been allocated
direction                = thesis.direction             # YES or NO

if direction == "YES":
    hypothetical_pnl = (hypothetical_exit_price - hypothetical_entry_price) * hypothetical_size_usdc
else:
    hypothetical_pnl = (hypothetical_entry_price - hypothetical_exit_price) * hypothetical_size_usdc
```

- **Positive `hypothetical_pnl`**: Restraint was wrong — missed a profitable trade
- **Negative `hypothetical_pnl`**: Restraint was correct — avoided a loss

## Aggregate No-Trade Alpha

```
no_trade_alpha_30d = sum(hypothetical_pnl for all restraints in window)
```

If `no_trade_alpha_30d` is strongly positive, the system is too conservative — it is over-rejecting good trades. This is surfaced to Olympus as a calibration signal to loosen gates.

If `no_trade_alpha_30d` is strongly negative, restraint is adding value — the rejections correctly avoided losses.

## On-Chain Contract

`NoTradeAlpha.sol` stores a permanent, tamper-proof ledger:

```solidity
mapping(bytes32 => int256) public hypotheticalPnl;    // restraintId => pnl (signed, 1e4 scaled)
int256 public cumulativeNoTradeAlpha;                  // running total
uint256 public restraintCount;

event CounterfactualResolved(
    bytes32 indexed restraintId,
    int256 hypotheticalPnl,
    uint256 resolutionTimestamp
);
```

## Dashboard

Web UI `/leaderboard` → "No-Trade Alpha" section:

| Metric | Value |
|--------|-------|
| Total restraints | 47 |
| Resolved restraints | 38 |
| Correct restraints (avoided loss) | 24 (63%) |
| Costly restraints (missed profit) | 14 (37%) |
| Total hypothetical PnL from restraints | -$1,420 (negative = good: avoided this much loss) |
| No-Trade Alpha 30d | +$340 (positive = added value by restraining) |

Note: "No-Trade Alpha 30d" uses sign convention where **positive means restraint added value** (i.e., negative `hypothetical_pnl` sum — avoided losses — is displayed as positive alpha).

## Policy Implications

Olympus monitors No-Trade Alpha weekly:
- If No-Trade Alpha is persistently negative (restraint is destroying value → missing good trades): Olympus proposes relaxing the `MIN_EDGE` or `MIN_CONFIDENCE` thresholds to Areopagus policy
- If No-Trade Alpha is persistently high positive: Areopagus is adding significant value from rejections — no change needed

Any threshold change requires ZeusMultisig approval (see `docs/RISK_POLICY.md`).
