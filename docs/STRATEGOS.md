# Strategos — Execution Service

The Strategos (Στρατηγός, "General") was the elected Athenian military commander who executed the council's strategy. In Pantheon Trades, Strategos routes approved theses to execution on the Polymarket CLOB.

## Responsibilities

1. Receive `ApprovalToken` from Areopagus
2. Estimate slippage and final fill price
3. Submit limit orders to Polymarket CLOB
4. Handle partial fills and order management
5. Emit `Trade` events on fill
6. Route to paper trading in simulation mode

## Live vs. Paper Routing

Strategos has two execution modes:

```python
class ExecutionRouter:
    def route(self, token: ApprovalToken, strategy: Strategy) -> Executor:
        if strategy.mode == "paper":
            return PaperExecutor(token)
        elif strategy.mode == "live":
            return LiveExecutor(token, clob_client=PolymarketCLOB())
```

A strategy must be in `LIVE` Moirai state to use `LiveExecutor`. Paper mode is the default for newly registered strategies.

## Order Construction

```python
def build_order(token: ApprovalToken, signal: Signal) -> Order:
    # Price: council probability adjusted for slippage budget
    estimated_slippage = slippage.estimate(
        market_id=token.market_id,
        size_usdc=token.final_size_usdc,
        orderbook=pythia.get_orderbook(token.market_id)
    )
    
    limit_price = round(
        token.council_probability - estimated_slippage * SLIPPAGE_BUFFER,
        2  # 2 decimal places (cent precision)
    )
    
    return Order(
        market_id=token.market_id,
        token_id=get_yes_token(token.market_id),  # or NO token if direction=NO
        side="BUY",
        price=limit_price,
        size=token.final_size_usdc,
        type="GTC",
        expiration=token.expires_at
    )
```

`SLIPPAGE_BUFFER = 1.5` — limit price set 1.5x estimated slippage below council probability for a conservative fill target.

## Slippage Estimation

`slippage.py` computes expected slippage by walking the orderbook:

1. Fetch orderbook from Pythia (cached, max 30s old)
2. Walk ask levels until cumulative size ≥ `final_size_usdc`
3. Compute volume-weighted average price
4. Slippage = VWAP - best_ask

If orderbook data is stale or the market is too thin, slippage estimate returns `ESTIMATE_UNAVAILABLE` → order rejected.

## Latency Tracking

`latency.py` records:
- `t0`: ApprovalToken received
- `t1`: Order submitted to CLOB
- `t2`: Order acknowledged by CLOB
- `t3`: Fill notification received

All latencies published to `strategos:latency` Redis stream and monitored by Argos.

## Paper Executor

Paper executor simulates fills without submitting to CLOB:
- Fill price = current Polymarket mid-price at time of "execution"
- Fill assumed immediate at mid-price (no slippage modeled in paper mode)
- Positions tracked in PostgreSQL with `mode = "paper"`
- Same `Trade` event schema as live trades

Paper trades are included in Ostrakon scoring and Elysium backtests.

## Order States

```
PENDING → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
                                   └→ EXPIRED (TTL exceeded)
                                   └→ CANCELLED (manual or Argos exit)
```

Argos monitors all SUBMITTED/ACKNOWLEDGED orders and alerts if not filled within 10 minutes.

## Error Handling

| Error | Action |
|-------|--------|
| CLOB API 429 | Retry with exponential backoff (max 3 retries) |
| CLOB API 5xx | Retry 3x; then reject with error trace |
| Orderbook stale | Reject; emit signal_expired event |
| Slippage too high | Reject; emit ProofOfRestraint |
| ApprovalToken expired | Reject; request new deliberation |

## Polymarket CLOB Client

`polymarket_clob.py` wraps the Polymarket API:
- Auth: API key via `POLYMARKET_API_KEY` env var
- Order submission, cancellation, status polling
- WebSocket subscription for fill notifications
- Orderbook streaming

See `docs/POLYMARKET_NOTES.md` for API details.
