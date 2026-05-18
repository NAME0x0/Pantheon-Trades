# Polymarket integration — what's wired, what's missing

You shared L2 trading credentials (API key + signing secret + passphrase).
This doc captures what those credentials enable, what they don't, and what
else is needed to flip `EXECUTION_MODE=live` on Polymarket.

## What you provided

- `POLYMARKET_API_KEY` — read + L2 trading scope (the "operator" key)
- `POLYMARKET_API_SECRET` — base64 signing secret for HMAC of trading requests
- `POLYMARKET_API_PASSPHRASE` — 32-byte passphrase that combines with the API
  key to produce the L2 auth header on every signed request

These are now in `.env` locally — **never committed**. `.env` is in `.gitignore`,
verified.

> **Treat these credentials as compromised the moment they leave a private channel.**
> A signing secret + passphrase is sufficient for anyone holding them to sign trades
> against your wallet. Rotate them via the Polymarket dashboard now if there's any
> chance they were observed, posted, or screenshotted anywhere.

## What's wired in the repo already

| Component | File | Status |
|-----------|------|--------|
| L2 order signing | `services/strategos/src/strategos/polymarket_clob.py` | Uses `py-clob-client`. Already passes the 3 creds via `ApiCreds`. Works with v1 client; v2 detection adds `post_only` + `builder_code` kwargs with TypeError fallback. |
| Maker rebate accounting | `services/strategos/src/strategos/maker_rebate.py` | Books fees + rebates per V2 fee schedule per category. |
| Builder-code attribution | `services/strategos/src/strategos/polymarket_builder.py` | Reads `POLYMARKET_BUILDER_CODE` + `POLYMARKET_BUILDER_PAYOUT` from env. **Not yet registered with Polymarket.** |
| Live executor | `services/strategos/src/strategos/live.py` | Routes ApprovalToken → signed order with post_only + builder_code + category. |
| Live WebSocket book | `services/strategos/src/strategos/polymarket_ws.py` (Tier A) | Reads L2 depth for the slippage learner. |
| Paper-trade harness | `scripts/paper_trade_polymarket.py` | Pulls Gamma + CLOB book, applies V2 fees. Synthetic fallback when geo-blocked. |

## What's still needed for live mode

### 1. Wallet private key for on-chain order signing
- **Env var:** `PRIVATE_KEY`
- **What:** the Polygon-side wallet that funds the Polymarket account.
  Polymarket order signing uses EIP-712 typed signatures; py-clob-client
  derives the signer from this key.
- **Funding required:** USDC on Polygon. The Polymarket dashboard shows
  your deposit address — fund it before flipping `EXECUTION_MODE=live`.

### 2. Polymarket builder-code registration (admin)
- **Env vars** (already coded, not registered):
  - `POLYMARKET_BUILDER_CODE` — short alphanumeric identifier (max 32 chars).
  - `POLYMARKET_BUILDER_PAYOUT` — 0x-prefixed Polygon address that receives
    the daily USDC builder fee payout.
- **What you need to do:** apply via the Polymarket dashboard for a builder
  program slot. They approve manually. Until approved, every fill we route
  earns $0 in builder fees — the code is signed onto the order but produces
  no revenue without the back-end registration.
- **Builder fees expected** (per Polymarket V2 schedule × MAKER_REBATE_SHARE=22%):
  - Crypto: 720 bps × 22% = **158 bps per fill**
  - Politics / Finance / Tech: 400 × 22% = **88 bps**
  - Sports: 300 × 22% = **66 bps**
  - Geopolitics / World events: 0 (fee-free category)

### 3. Geo-block workaround
- **Problem:** Polymarket blocks IPs from your current location (confirmed via
  DNS resolves OK but HTTP connection refused; Manifold + Kalshi + CoinGecko
  all reachable from the same host).
- **Options:**
  - **Cloud function proxy** — deploy a Vercel / Cloudflare Worker / fly.io edge
    function in a permitted region that proxies the Polymarket REST + CLOB
    calls. ~$0/month at our volume. Easiest path.
  - **VPS in a permitted region** — DigitalOcean / Hetzner $5/month box.
  - **Residential VPN** — works but introduces latency that hurts the maker-
    rebate path (post_only orders need fast cancel responsiveness).
- **No code change needed** — `POLYMARKET_HOST` env var already points the
  CLOB client at any host, so a proxy is a single env-var flip.

### 4. Network selection
- **Polymarket runs on Polygon (chain id 137) for L2 settlement.**
- Pantheon's existing chain plumbing targets **Arc Testnet** (chain id 5042002)
  for the Proof-of-Restraint witnesses. These are independent — Arc anchors
  the council's decisions while Polygon hosts the actual CLOB.
- Required env vars when live:
  - `POLYMARKET_CHAIN_ID=137` (Polygon mainnet)
  - `POLYMARKET_HOST=https://clob.polymarket.com` (or the proxy URL)
  - `RPC_URL=https://polygon-rpc.com` (or any Polygon RPC; for the wallet's
    signing path)

### 5. CLOB v2 migration (recommended within the next 30 days)
- Polymarket rolled out CLOB v2 on **April 28 2026** with EIP-712 domain
  bumped from "1" to "2". V1 signatures will eventually stop validating.
- **Migration path:**
  - `pip install py-clob-client-v2` (already documented at
    `https://github.com/Polymarket/py-clob-client-v2`).
  - Our `polymarket_clob.py` already uses the v2 kwarg names (`post_only`,
    `builder_code`); they're plumbed with TypeError fallback so the v1
    client silently ignores them. v2 client respects them.
  - No code change beyond the install — the env contract is identical.

### 6. pUSD collateral migration (optional, Polymarket V2)
- Polymarket V2 introduced **pUSD** — a 1:1-USDC-backed ERC-20 specific to
  the Polymarket exchange. Existing USDC deposits are wrapped to pUSD on
  the first trade after migration. Bridge / unbridge UI is on the
  Polymarket dashboard.
- **Operator impact:** if you already have USDC in the Polymarket account,
  it's converted to pUSD on first L2 trade. Withdrawals unwrap back to USDC.
  Nothing for you to do unless you want to pre-migrate manually.

## What I need from you to ship live trading

1. ✅ **API key + signing secret + passphrase** — received, in `.env`.
2. ❌ **`PRIVATE_KEY`** for the wallet that funds the Polymarket account.
3. ❌ **Geo-block decision** — proxy / VPS / VPN? My recommendation: Vercel
   edge function (free, ~50 lines, ~1 hour to deploy).
4. ❌ **Builder-code approval from Polymarket** — apply via their dashboard.
5. ❌ **`POLYMARKET_BUILDER_PAYOUT` address** — pick a Polygon wallet you
   control (can be the same as the trading wallet).
6. ❌ **USDC funded into the Polymarket account** — start with a small test
   amount like $100.
7. ❌ **Initial `EXECUTION_MODE=live` decision** — only flip after a 30-day
   `EXECUTION_MODE=paper` run against live flow with positive PnL on the
   paper book.

## Security checklist

Before any of the above is wired into production:

- [ ] Confirm `.env` is in `.gitignore` (✅ already verified)
- [ ] Confirm no committed file contains the live secret (run
      `git log -p | grep "Zit0FB9I"` — should be empty)
- [ ] Add Mozilla SOPS + age encryption to `.env.enc` for any non-local
      deployment (`infra/secrets/` scaffolding exists — see Tier E)
- [ ] Use a SEPARATE wallet for Pantheon, not your main wallet
- [ ] Cap the trading wallet's USDC balance at a value you'd accept
      losing entirely if the bot misbehaves
- [ ] Rotate `POLYMARKET_API_SECRET` quarterly even with no incident
- [ ] Set `MAX_POSITION_PCT=0.02` (2%) for the first 30 days of live,
      not the constitutional 5% cap

## Cost projection at scale

If everything ships and you start small ($1000 paper-bankroll-equivalent on
live, 5 fills/day average, mostly politics + sports):

- Daily notional: ~$1000 × 0.05 (size) × 5 (fills) = **$250 per day**
- Annual notional: ~$91k
- All-taker round-trip cost: ~3% blended (politics 4% + sports 3% + geo 0%)
- Maker-rebate path (50% maker mix): saves ~80 bps per round-trip = **~$730/yr saved**
- Builder-code revenue at 88 bps blended × $91k = **~$800/yr earned**
- Total fee-side benefit: **~$1.5k/yr** on a $1k bankroll
- Council edge contribution: unknown — depends on the live Brier work

This is the structural alpha number. The actual PnL upside (or downside) from
the council's directional calls is what the next 30 days of paper trade
against live flow tells us.
