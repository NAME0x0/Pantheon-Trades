# Signal Specification

Signals are the primary output of Apollo and the primary input to Boule. Every trade begins with a signal.

## Signal Schema

```python
class Signal(BaseModel):
    signal_id: str                    # uuid4
    market_id: str                    # Polymarket condition ID (0x...)
    question: str                     # Human-readable market question
    category: str                     # "crypto" | "politics" | "sports" | "science" | "other"
    
    # Probability estimates
    market_probability: float         # Current Polymarket mid-price (0.0 - 1.0)
    oracle_probability: float         # Apollo's model estimate
    edge: float                       # oracle_probability - market_probability
    edge_abs: float                   # abs(edge)
    
    # Band classification
    band: str                         # "S" | "A" | "B" | "C" | "D"
    band_score: float                 # 0.0 - 1.0 composite score
    
    # Feature scores (all 0.0 - 1.0)
    liquidity_score: float            # Orderbook depth score
    volatility_score: float           # Current volatility regime
    catalyst_score: float             # Proximity to known catalyst event
    sentiment_score: float            # Aggregated sentiment signal
    correlation_score: float          # Independence from existing positions
    trend_score: float                # Price trend alignment
    
    # Market metadata
    volume_24h: float                 # 24h trading volume in USDC
    open_interest: float              # Total open interest in USDC
    bid: float                        # Best bid
    ask: float                        # Best ask
    spread: float                     # ask - bid
    resolution_date: datetime | None  # When market resolves
    days_to_resolution: float | None  # Computed from resolution_date
    
    # Source data
    data_sources: list[str]           # Which Pythia sources contributed
    staleness_seconds: int            # Age of freshest data point
    source_trust_score: float         # 0.0 - 1.0 weighted trust of sources
    
    # Timestamps
    created_at: datetime
    pythia_snapshot_at: datetime      # When raw data was fetched
```

## Band Classification

Bands classify markets by combined signal quality. Only S and A bands proceed to Boule deliberation.

| Band | Edge | Liquidity | Composite Score | Action |
|------|------|-----------|-----------------|--------|
| S | > 0.15 | > 0.80 | > 0.85 | → Boule |
| A | > 0.08 | > 0.60 | > 0.70 | → Boule |
| B | > 0.05 | > 0.40 | > 0.55 | Monitor only |
| C | > 0.02 | > 0.20 | > 0.40 | Log only |
| D | ≤ 0.02 | any | ≤ 0.40 | Discard |

Band score is a weighted composite:
```
band_score = (
    0.35 * edge_abs_normalized +
    0.20 * liquidity_score +
    0.15 * catalyst_score +
    0.15 * sentiment_score +
    0.10 * trend_score +
    0.05 * correlation_score
)
```

## Edge Calculation

Edge = Apollo oracle probability - Polymarket market probability.

Apollo oracle probability is computed from:
1. Base probability from historical resolution rates for similar markets
2. Adjusted by sentiment signal (Reddit, CoinDesk, Bloomberg)
3. Adjusted by technical momentum (trend_score)
4. Adjusted by catalyst proximity (catalyst_score)
5. Calibrated against Ostrakon historical Brier scores

Positive edge → market is underpricing YES. Negative edge → overpricing YES (short opportunity).

Only edges with `|edge| > 0.05` and `edge_abs_normalized > 0.3` are eligible for band S/A.

## Liquidity Score

Computed by `features/liquidity.py`:

```
liquidity_score = sigmoid(
    0.4 * log(volume_24h / VOLUME_BASELINE) +
    0.4 * log(open_interest / OI_BASELINE) +
    0.2 * (1 - spread / SPREAD_MAX)
)
```

Where:
- `VOLUME_BASELINE` = $50,000 USDC/day
- `OI_BASELINE` = $100,000 USDC
- `SPREAD_MAX` = 0.10 (10 percentage points)

## Staleness Policy

Signals with `staleness_seconds > 300` (5 minutes) are marked stale and cannot proceed to Boule.

Sources and their max staleness thresholds:
- Polymarket CLOB: 60s
- Crypto prices: 30s
- News feeds: 300s
- Reddit: 600s
- DeFiLlama: 120s

Stale source data degrades `source_trust_score` proportionally.

## Signal Lifecycle

```
Generated → Scored → Banded → Queued → Sent to Boule
                                  └→ Expired (if not consumed within TTL)
```

Signal TTL: 15 minutes. If Boule has not consumed a signal within TTL, it is expired and a fresh signal must be generated.

## Signal Events (Redis Stream)

Stream key: `apollo:signals`

Events:
- `signal.created` — new signal generated
- `signal.banded` — band score computed
- `signal.expired` — TTL exceeded
- `signal.consumed` — Boule picked up for deliberation
