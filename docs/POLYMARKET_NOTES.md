# Polymarket Notes

Operational notes for the Polymarket CLOB integration.

## API

Polymarket runs a Central Limit Order Book (CLOB) on Polygon. Key endpoints used:

- **Markets**: `GET /markets` — list active markets with current prices
- **Orderbook**: `GET /book?token_id={id}` — full orderbook depth
- **Trades**: `GET /trades?market={id}` — recent trade history
- **Orders**: `POST /order` — submit limit or market order
- **Positions**: `GET /positions` — current open positions

Auth: API key via header. Keys issued per account.

CLOB address: `https://clob.polymarket.com`

## Market Structure

Each Polymarket event has:
- A **condition ID** (bytes32 hash) — used as `market_id` in Pantheon
- Two outcome tokens: YES (resolves to $1 if YES) and NO (resolves to $1 if NO)
- Prices quoted in USDC as probability (0.01 to 0.99)

YES token price = implied probability of YES resolution.

## Order Types

Pantheon Trades uses **limit orders** only. No market orders (slippage risk too high on thin books).

Order params:
```python
{
    "token_id": "YES_token_address",
    "price": 0.72,           # Limit price in USDC
    "size": 400.00,          # Size in USDC
    "side": "BUY",           # BUY = long YES
    "type": "GTC",           # Good Till Cancelled
    "expiration": 1704067200 # Unix timestamp
}
```

## Slippage

Strategos estimates slippage before submitting:
- Fetches full orderbook depth from Pythia
- Estimates fill price based on cumulative depth at each price level
- If estimated fill price deviates > `SLIPPAGE_TOLERANCE` from limit price, rejects

Default `SLIPPAGE_TOLERANCE`: 0.02 (2 percentage points).

## Settlement

Polymarket uses UMA Optimistic Oracle for resolution. Resolution is typically:
1. Proposed outcome submitted to UMA
2. 2-hour dispute window
3. If not disputed, resolves
4. If disputed, UMA voters decide within 48h

Winning token holders can redeem at $1.00 USDC per share after resolution.

Pantheon does not auto-redeem. Strategos handles redemption on detected resolution.

## Liquidity Thresholds

Markets below these thresholds are excluded from signal generation:
- Min 24h volume: $10,000 USDC
- Min open interest: $25,000 USDC
- Min orderbook depth (±5 ticks): $5,000 USDC per side

These are `liquidity.py` filter constants in Apollo.

## Resolution Sources

Polymarket categories and their typical resolution data sources:
- **Crypto**: CoinGecko, Binance official feeds
- **Politics**: AP News, official election authority data
- **Sports**: Official league results
- **Science**: Published papers, WHO/CDC announcements

Pythia cross-checks market resolution status against these sources for early exit signal.

## Rate Limits

Polymarket CLOB API:
- Public endpoints: 10 req/s
- Authenticated endpoints: 5 req/s per API key

Pythia implements exponential backoff on 429 responses.

## Known Issues

- **Weekend liquidity**: Prediction market liquidity drops ~60% on weekends for crypto markets. Liquidity score adjustment applied (multiplied by 0.7 for Saturday/Sunday)
- **Resolution delays**: Some markets have oracle disputes that delay resolution by 2-5 days beyond expected date. Argos handles this by extending max_hold_days when resolution delay is detected
- **Price manipulation**: Thin markets (OI < $50K) susceptible to price manipulation. Correlation feature in Apollo flags correlated price movements to detect potential manipulation
