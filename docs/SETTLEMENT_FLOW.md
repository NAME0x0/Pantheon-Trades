# Settlement Flow

How a trade goes from approved Thesis to on-chain settlement.

## Flow Overview

```
1. Areopagus issues ApprovalToken
        │
        ▼
2. Strategos submits limit order to Polymarket CLOB
        │
        ▼
3. Order fills → Trade event emitted
        │
        ▼
4. Argos begins monitoring position
        │
        ▼
5. Market resolves on Polymarket
        │
        ▼
6. Settlement payout received (USDC)
        │
        ▼
7. Parthenon archives outcome
        │
        ▼
8. Ostrakon scores agents
        │
        ▼
9. Elysium computes counterfactual
        │
        ▼
10. On-chain: TradeProof.settle() called
```

## Step-by-Step

### Step 1: Approval
Areopagus validates the Thesis and issues an `ApprovalToken`:
```json
{
  "token_id": "uuid4",
  "thesis_id": "...",
  "final_size_pct": 0.04,
  "final_size_usdc": 400.00,
  "direction": "YES",
  "expires_at": "2024-01-01T00:15:00Z"
}
```
Token expires in 15 minutes. Strategos must use it within that window.

### Step 2: Order Submission
Strategos calls Polymarket CLOB with a limit order:
- Price: `council_probability ± slippage_budget`
- Size: `final_size_usdc`
- Side: `BUY` (for YES) or `SELL` (for NO)

Orders are GTC (Good Till Cancelled) with TTL matching the signal TTL.

### Step 3: Fill
On fill, Polymarket CLOB returns a fill confirmation. Strategos emits `Trade` event to Redis stream `strategos:trades`.

`TradeProof.sol` is called with the fill data:
```solidity
function recordTrade(
    bytes32 thesisHash,
    bytes32 marketId,
    uint256 sizeUsdc,
    uint256 fillPrice,
    uint256 timestamp
) external
```

### Step 4: Position Monitoring
Argos subscribes to `strategos:trades` and begins polling position PnL every 30 seconds.

Argos watches for:
- Target hit (current probability ≥ `exit_conditions.target`)
- Stop hit (current probability ≤ `exit_conditions.stop`)
- Max hold days exceeded
- Invalidation event from Cassandra warning
- Manual override from Olympus

### Step 5: Market Resolution
Polymarket resolves markets via UMA oracle. Resolution produces:
- Final outcome: YES = 1.0, NO = 0.0
- USDC payout to position holders

### Step 6: Archive
Parthenon receives the `Trade` event and resolution outcome, computes:
- `outcome_usdc`: final payout
- `pnl_usdc`: outcome - cost basis
- `pnl_pct`: percentage return on capital risked
- `resolution_probability`: 1.0 or 0.0

Archives full outcome to IPFS. Adds to daily Merkle tree.

### Step 7: Scoring
Ostrakon receives the resolution event and updates:
- Brier score for each council agent (using their `probability_estimate` vs. actual outcome)
- Sharpe ratio running averages
- Leaderboard

Updated scores published to `ostrakon:scores` Redis stream, consumed by Boule memory.

### Step 8: Counterfactual
If the trade was a ProofOfRestraint (no-trade), Elysium computes what would have happened.

For executed trades, Elysium validates that the actual outcome was within the expected range given the thesis confidence.

### Step 9: On-Chain Settlement Record
`TradeProof.settle()` called with final outcome:
```solidity
function settle(
    bytes32 tradeId,
    uint256 resolutionValue,   // 1e18 for YES, 0 for NO
    uint256 payoutUsdc,
    bytes calldata proof        // UMA oracle proof hash
) external
```

This creates a permanent on-chain record linking: thesis → approval → trade → settlement.

## Proof of Restraint Settlement

When Areopagus rejects a thesis for a band S/A signal, `ProofOfRestraint.sol` is called:
```solidity
function recordRestraint(
    bytes32 signalHash,
    bytes32 thesisHash,
    bytes32 rejectionReason,
    uint256 signalEdge,        // scaled 1e4
    uint256 timestamp
) external
```

After market resolution, `NoTradeAlpha.sol` records the counterfactual:
```solidity
function recordCounterfactual(
    bytes32 restraintId,
    uint256 resolutionValue,
    int256 hypotheticalPnl     // signed: positive = good not to trade
) external
```

## Failure Cases

| Failure | Handling |
|---------|---------|
| Order not filled within TTL | Order cancelled; thesis expires; ProofOfRestraint issued |
| Partial fill | Position tracked at actual size; stop/target adjusted proportionally |
| Polymarket resolution delayed | Argos extends max_hold_days; sends alert to Olympus |
| CLOB API error | Strategos retries 3x with exponential backoff; then rejects with error trace |
| Arc RPC failure | Parthenon queues on-chain calls; retries on reconnect |
