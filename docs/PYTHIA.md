# Pythia — Data Oracle

The Pythia was the Oracle of Delphi — the source of prophetic truth in ancient Greece. In Pantheon Trades, Pythia is the data ingestion service that provides all market data, news, and signals to the rest of the system.

## Data Sources

| Source | Data Type | Poll Interval | Max Staleness |
|--------|-----------|---------------|---------------|
| Polymarket CLOB | Markets, orderbooks, prices, trades | 60s | 60s |
| CoinGecko / Binance | Crypto prices, volume | 30s | 60s |
| DeFiLlama | TVL, protocol metrics, DEX volumes | 2 min | 5 min |
| Bloomberg (via feed) | News headlines, event data | 5 min | 15 min |
| CoinDesk | Crypto news | 5 min | 15 min |
| Reddit | r/CryptoCurrency, r/Polymarket sentiment | 10 min | 30 min |
| Hyperliquid | Derivatives positioning, funding rates | 2 min | 5 min |

## Source Trust Scoring

Each source has a trust score based on:
- Historical accuracy (validated against market resolutions)
- Uptime reliability
- Latency consistency

Trust scores degrade linearly with staleness and reset on fresh data.

```python
trust_score = base_trust * staleness_factor
staleness_factor = max(0.0, 1.0 - (staleness_seconds / max_staleness_seconds))
```

## Staleness Sentinel

`staleness.py` monitors all source health. If any source exceeds its max staleness:
1. Affected signals are flagged with degraded `source_trust_score`
2. Staleness sentinel event emitted to Olympus
3. If critical source (Polymarket CLOB) is stale, Apollo pauses signal generation

See `docs/STALENESS_SENTINEL.md`.

## Cache

`cache.py` implements a tiered cache:
- **L1**: In-memory LRU (< 60s for price data)
- **L2**: Redis (< 5 min for market snapshots)
- **L3**: PostgreSQL (full history)

Cache keys are deterministic: `{source}:{market_id}:{data_type}:{rounded_timestamp}`.

## Rate Limiting

`rate_limit.py` enforces per-source rate limits:
- Token bucket per source
- Exponential backoff on 429 responses
- Jitter to prevent synchronized bursts

## MarketSnapshot Schema

```python
class MarketSnapshot(BaseModel):
    market_id: str
    question: str
    category: str
    
    # Prices
    yes_price: float        # Best bid for YES token
    no_price: float         # Best bid for NO token
    mid_price: float        # (yes_price + no_price) / 2 — not always 0.5+0.5
    spread: float
    
    # Depth
    bid_depth_5pct: float   # Total USDC available within 5% of mid (bids)
    ask_depth_5pct: float   # Total USDC available within 5% of mid (asks)
    
    # Volume
    volume_24h: float
    volume_7d: float
    
    # Open interest
    open_interest: float
    
    # Resolution
    resolution_date: datetime | None
    resolution_source: str | None
    
    # Metadata
    sources: list[str]
    fetched_at: datetime
    staleness_seconds: int
```

## Service Files

`services/pythia/`:
- `base.py` — abstract source interface
- `polymarket.py` — Polymarket CLOB client
- `crypto.py` — CoinGecko/Binance price feeds
- `news.py` — news feed aggregator
- `defillama.py` — DeFiLlama client
- `bloomberg.py` — Bloomberg feed client
- `coindesk.py` — CoinDesk RSS/API client
- `reddit.py` — Reddit API client
- `hyperliquid.py` — Hyperliquid API client
- `cache.py` — multi-tier caching
- `rate_limit.py` — rate limiting per source
- `health.py` — health check endpoint
- `staleness.py` — staleness monitoring
- `source_trust.py` — trust score computation
