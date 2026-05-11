# Argos — Position Monitor

Argos (Ἄργος, the hundred-eyed giant) was the all-seeing guardian in Greek mythology. In Pantheon Trades, Argos watches all open positions and manages exits.

## Responsibilities

1. Subscribe to `strategos:trades` stream for new positions
2. Poll each open position for current PnL and market probability
3. Trigger exits based on target, stop, invalidation, or max hold
4. Adjust stops on partial fills
5. Alert Olympus on anomalies

## Position Monitoring Loop

```python
async def monitor_loop():
    while True:
        positions = await db.get_open_positions()
        for position in positions:
            snapshot = await pythia.get_market_snapshot(position.market_id)
            await evaluate_position(position, snapshot)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)  # default: 30s
```

## Exit Triggers

### Target Hit
```python
if current_probability >= exit_conditions.target:
    # For YES position: current_probability means the market is pricing you correctly
    # Time to exit at profit
    await exit(position, reason="TARGET_HIT")
```

### Stop Hit
```python
if current_probability <= exit_conditions.stop:
    await exit(position, reason="STOP_HIT")
```

### Max Hold Exceeded
```python
if days_open >= exit_conditions.max_hold_days:
    await exit(position, reason="MAX_HOLD_EXCEEDED")
```

### Invalidation Event
Argos subscribes to `boule:invalidation` events. If Boule detects that an open position's thesis has been invalidated (e.g., Cassandra warning materialized), Argos exits immediately.

### Areopagus Override
Areopagus can push exit signals for open positions that are now in violation of updated risk policy.

### Olympus Kill Switch
Emergency pause propagated from Olympus → Argos exits all positions in orderly fashion.

## PnL Calculation

```python
def compute_pnl(position: Position, snapshot: MarketSnapshot) -> PnLRecord:
    if position.direction == "YES":
        unrealized_pnl = (snapshot.mid_price - position.entry_price) * position.size_usdc
    else:
        unrealized_pnl = (position.entry_price - snapshot.mid_price) * position.size_usdc
    
    return PnLRecord(
        position_id=position.id,
        unrealized_pnl=unrealized_pnl,
        unrealized_pct=unrealized_pnl / position.size_usdc,
        current_probability=snapshot.mid_price,
        timestamp=now()
    )
```

PnL records written to PostgreSQL every 30s. Published to `argos:pnl` Redis stream for web UI.

## Stop Adjustments

Argos implements trailing stop logic:
- If position is profitable (unrealized PnL > 20% of cost), raise stop to breakeven
- If position is >40% profitable, raise stop to lock in 50% of gains
- Adjusted stops cannot be lowered (one-directional trailing)

Stop adjustments are logged and reflected in the open position view on the web UI.

## Exit Execution

Argos sends `ExitSignal` to Strategos, which submits a market or limit order to close:

```python
ExitSignal(
    position_id=position.id,
    market_id=position.market_id,
    direction="SELL",  # Sell the YES token
    size=position.current_size_usdc,
    reason=exit_reason,
    urgency="normal"  # or "urgent" for stop/invalidation
)
```

`urgency="urgent"` allows market orders for emergency exits (Areopagus override, Olympus kill switch).

## Anomaly Detection

Argos alerts Olympus if:
- Position PnL drops > 50% in a single poll interval
- Market probability moves > 20 percentage points since last poll
- Market goes stale (no orderbook activity for > 10 minutes)
- Resolution date passes without market resolving

## Service Files

`services/argos/`:
- `monitor.py` — main monitoring loop
- `pnl.py` — PnL calculation
- `exits.py` — exit trigger logic
- `adjustments.py` — stop adjustment logic
