# Pythia — Data Oracle

Data ingestion service. Polls all external data sources and provides normalized market snapshots.

## What It Does

1. Polls Polymarket CLOB for market data (prices, orderbooks, volume)
2. Fetches crypto prices, DeFiLlama TVL, news from Bloomberg/CoinDesk, Reddit sentiment, Hyperliquid positioning
3. Normalizes into `MarketSnapshot` objects
4. Manages per-source caching, rate limiting, staleness monitoring, and trust scoring
5. Serves data to Apollo and other services

## Setup

```bash
cd services/pythia
cp .env.example .env
# Requires POLYMARKET_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, BLOOMBERG_API_KEY, COINDESK_API_KEY
uv run python -m pythia
```

## Structure

```
src/pythia/
  base.py           Abstract source interface
  polymarket.py     Polymarket CLOB client
  crypto.py         CoinGecko/Binance price feeds
  news.py           News feed aggregator
  defillama.py      DeFiLlama client
  bloomberg.py      Bloomberg feed client
  coindesk.py       CoinDesk client
  reddit.py         Reddit API client
  hyperliquid.py    Hyperliquid client
  cache.py          Multi-tier cache (memory + Redis + PostgreSQL)
  rate_limit.py     Per-source rate limiting
  health.py         Health endpoint
  staleness.py      Staleness sentinel
  source_trust.py   Source trust scoring
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/PYTHIA.md` — full service documentation
- `docs/STALENESS_SENTINEL.md` — staleness monitoring
