# Apollo — Signal Engine

Apollo, the god of truth and light, was also the patron of the Oracle of Delphi. In Pantheon Trades, Apollo is the signal generation engine that transforms raw market data from Pythia into ranked trading opportunities.

## Responsibilities

1. Score each active Polymarket market across 6 feature dimensions
2. Compute edge (probability mispricing)
3. Classify markets into signal bands (S, A, B, C, D)
4. Filter noise; publish only S/A bands to Boule
5. Track band distribution over time for calibration

## Feature Modules

`services/apollo/src/apollo/features/`:

### `edge.py` — Edge Score
Computes the probability mispricing between Apollo's oracle estimate and the Polymarket market price.

Oracle estimate inputs:
- Base rate from historical resolution data for similar markets
- Sentiment adjustment from Reddit/news
- Technical momentum adjustment
- Catalyst proximity adjustment
- Calibration factor from Ostrakon historical scores

### `liquidity.py` — Liquidity Score
Scores the depth and quality of the orderbook:
- Volume 24h (log-normalized vs. $50K baseline)
- Open interest (log-normalized vs. $100K baseline)
- Spread quality (1 - spread/MAX_SPREAD)
- Bid/ask depth balance

### `volatility.py` — Volatility Score
Scores the current volatility regime:
- Recent price movement (standard deviation of hourly mid-prices)
- Volatility vs. historical baseline for this market category
- **High volatility**: higher score (more opportunity) but also triggers Cassandra flags
- Extreme volatility (> 3σ from baseline): capped score + mandatory Cassandra flag

### `catalyst.py` — Catalyst Score
Proximity to known catalyst events:
- Economic calendar events (Fed decisions, earnings, elections)
- Crypto-specific events (halving, major protocol upgrades, token unlocks)
- Sports schedules, political deadlines
- Score peaks in the 3-14 day window before the event

### `sentiment.py` — Sentiment Score
Aggregated sentiment signal:
- Reddit sentiment (r/CryptoCurrency, r/Polymarket): TextBlob/VADER scoring
- News headline sentiment: Bloomberg, CoinDesk
- Hyperliquid: funding rate as market sentiment proxy
- Weighted combination normalized to [0, 1]

### `correlation.py` — Correlation Score
Independence from existing open positions:
- Low correlation to existing YES positions → high score (diversification benefit)
- High correlation to existing positions → low score (concentration risk)
- Uses cosine similarity on market feature vectors

### `trend.py` — Trend Score
Directional momentum alignment:
- Short-term price trend (7-day MA vs. 30-day MA)
- Volume trend (is volume increasing?)
- Whether trend direction aligns with the proposed trade direction

## Band Scoring

```python
band_score = (
    0.35 * edge_abs_normalized +
    0.20 * liquidity_score +
    0.15 * catalyst_score +
    0.15 * sentiment_score +
    0.10 * trend_score +
    0.05 * correlation_score
)
```

Band thresholds: S > 0.85, A > 0.70, B > 0.55, C > 0.40, D ≤ 0.40

## Signal Bands

`bands.py` — band classification and management:
- Classifies signals by band score
- Tracks band history per market
- Detects band upgrades/downgrades (significant events → Olympus notification)

## Scorer

`scorer.py` — main scoring orchestrator:
- Fetches fresh `MarketSnapshot` from Pythia for each market
- Runs all 6 feature modules in parallel
- Assembles final `Signal` with band classification
- Publishes to `apollo:signals` Redis stream

## Filters

`filters.py` — pre-scoring filters:
- Exclude markets with open interest < $25K
- Exclude markets resolving in < 2 days or > 180 days
- Exclude markets with no resolution date
- Exclude markets that are already in deliberation queue

## CLI

```bash
# Score all markets once
cd services/apollo && uv run python -m apollo.cli score

# Continuous scan with 60s interval
cd services/apollo && uv run python -m apollo.cli run --interval 60

# Score a specific market
cd services/apollo && uv run python -m apollo.cli score --market-id 0xabc...
```
