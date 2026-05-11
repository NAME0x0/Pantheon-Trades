# MEV Notes

Maximal Extractable Value (MEV) considerations for Pantheon Trades on Arc Testnet / Polymarket.

## Context

Pantheon Trades operates on two separate chains/platforms:
1. **Polymarket CLOB** (order book trading) — MEV via front-running/sandwich attacks
2. **Arc Testnet** (on-chain records) — MEV via transaction ordering

## Polymarket CLOB MEV

Polymarket uses a centralized CLOB, not an AMM. This means:
- No sandwich attacks (no slippage on AMM pools)
- Front-running risk exists: if a large order is visible before execution, a faster participant can take the better price

### Mitigations

1. **Thesis registration after order**: `ThesisRegistry.sol` is called *after* order submission, not before. The on-chain signal is not predictive of the order.

2. **Limit orders only**: Pantheon never submits market orders. Limit price is set conservatively (1.5x estimated slippage away from mid). Even if someone sees the order, they must accept worse-than-mid pricing to front-run.

3. **Order size capped**: Max position 5% of portfolio. Order sizes are not large enough to materially move thin markets.

4. **Private order submission**: Polymarket API key auth prevents public order book spoofing. Orders are visible to CLOB matching engine only until matched.

## Arc Testnet MEV

Arc Testnet is an EVM chain. On-chain transactions are public in the mempool.

### What we post on-chain

All calls to Pantheon contracts are *records*, not execution triggers:
- `ThesisRegistry.register()` — records that a thesis was approved (after order placed)
- `TradeProof.recordTrade()` — records a fill (after fill confirmed)
- `ProofOfRestraint.recordRestraint()` — records no-trade (after decision made)

None of these calls trigger fund movements or CLOB interactions. There is no profit available from front-running these transactions.

### Gas Costs

Gas on Arc Testnet is paid in USDC. Parthenon batches on-chain calls to minimize gas:
- Thesis registrations: batch at end of each hour
- Daily Merkle root: single call per day
- Reputation updates: batch post-resolution

## Conclusion

The architecture deliberately separates on-chain records from CLOB execution. There is no profitable MEV attack on the trade execution path. The only MEV risk is potential information leakage if an attacker can infer trade intent from on-chain activity — mitigated by the post-execution registration ordering.

If the system were to use on-chain AMM liquidity in the future, this analysis would need to be revisited.
