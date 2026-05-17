# Artifacts

Captured live-test outputs from `scripts/live_test_gemini.py`. Each
file is a JSON snapshot of one deliberation run against the Gemini
API, with per-call timing, token counts, and an estimated USD cost.

## Schema

```
{
  "schema": "pantheon-live-test-v1",
  "model":         "gemini-flash-lite-latest",
  "started_at":    "2026-05-17T03:42:19.890159+00:00",
  "finished_at":   "2026-05-17T03:48:23.841087+00:00",
  "total_duration_ms": 363950,
  "spacing_seconds_between_calls": 8.0,
  "signal":  { ... thesis-bearing signal ... },
  "rounds":  [
    {
      "round": 1,
      "agents": [
        { agent, http_status, duration_ms, tokens_in, tokens_out,
          model_version, preview, finish_reason, retried_429 },
        ...
      ]
    },
    { "round": 4, ... }
  ],
  "tokens": { "in": 12345, "out": 4567 },
  "cost_usd_estimate":  0.00266,
  "pricing_assumed":    { input_per_mtok: 0.10, output_per_mtok: 0.40 },
  "failure_count":      0,
  "agent_count":        10
}
```

## Captured runs

### `live_test_20260517T034219Z.json` (canonical)
- model: `gemini-flash-lite-latest` (resolved to `gemini-3.1-flash-lite`)
- 10 agents × 2 rounds (opening + vote) = 20 calls
- failures: 0
- total duration: 363,950 ms (~6 min)
- spacing: 8.0 s between calls (free-tier compliant)
- tokens: 12,000+ in / 4,500+ out
- estimated cost: **$0.00266**

This is the canonical successful baseline. Every agent (ares, athena,
hades, cassandra, zeus, solon, themis, hephaestus, humans, eris) emits
a round-1 opening and a round-4 vote with all required fields.

### `live_test_20260517T020122Z.json` (partial)
- model: `gemini-2.5-flash-lite`
- 20 calls, 16 OK, 4 RPM-throttled (HTTP 429)
- demonstrates the retry-on-429 path with `Please retry in Xs` parsing

Kept as the canonical *throttled-tier* artifact — useful for showing
what a deliberation looks like on the free-tier rate ceiling.

## Reproducing

```bash
# 10 agents × 2 rounds, ~6 minutes on free tier
uv run --project services/boule --with httpx python scripts/live_test_gemini.py

# Slimmer roster + tighter spacing on a paid tier
LIVE_TEST_ROSTER="ares,athena,zeus,solon,eris" \
LIVE_TEST_SPACING_S=2 \
BOULE_GEMINI_MODEL=gemini-2.5-flash-lite \
uv run --project services/boule --with httpx python scripts/live_test_gemini.py
```

`gemini-flash-lite-latest` resolves to whichever flash-lite SKU Google
currently calls "latest" (Gemini 3.1 flash-lite as of 2026-05). Pin
explicitly with `BOULE_GEMINI_MODEL=gemini-2.5-flash-lite` for
deterministic comparison runs.

---

## CoinGecko paper-trade artifacts

The harness in `scripts/live_paper_trade_coingecko.py` walks the real
BTC/USD bar series from CoinGecko's free `/coins/{id}/market_chart`
endpoint, builds a synthetic "will next tick be higher?" binary
question for each bar, sizes a paper trade with the production
half-Kelly + caps, fills it through the production `PaperBook` with
half-spread + slippage + 2% taker fees, and settles on the next bar.

### `coingecko_paper_20260517T091551Z.json` (canonical)
- mode: `history`, 7-day window, 100 hourly bars (BTC ≈ $78,000 range)
- edge threshold: 2% absolute  ·  momentum lookback: 3 bars
- bankroll: $10,000 USDC  ·  synthetic CLOB depth: $50,000
- trades fired: **79**  ·  settled: 79  ·  wins: 39  ·  losses: 40
- win rate: 49.4%  ·  realised PnL: **–$3,951.20** (–39.5%)
- fees paid: **$1,346.52** (entry + exit at 2% each on every trade)
- max drawdown: 56.8%  ·  sharpe (raw, per-tick): –0.11

**What this proves:** the full sizing/execution pipeline runs end-to-end
on real data. **What this shows:** naive momentum is not profitable as
a binary tick predictor — taker fees alone are 4% round-trip, and the
half-spread + slippage push every break-even slightly negative even
when the directional call is right. *This is exactly the kind of result
the council-driven flow is meant to filter out: 79 trades that would
not pass Areopagus gates in production because the edge does not survive
costs.*

The point of the artifact is honesty: the plumbing is real, the data is
real, and the strategy in the harness is intentionally a toy so the
result is not flattering. Replace the `council_probability()` function
with an actual Boule deliberation and you can rerun the same harness
with real council probabilities — but that costs LLM tokens.

### Reproducing

```bash
# Single API call, 7-day history window, 100 hourly bars
LIVE_PAPER_MODE=history LIVE_PAPER_DAYS=7 \
LIVE_PAPER_TICKS=100 LIVE_PAPER_EDGE_THRESHOLD=0.02 \
python scripts/live_paper_trade_coingecko.py

# Live polling (each tick = one API call; trips CoinGecko free-tier
# limits past ~6 calls — keep TICK_S high or use a Pro key).
LIVE_PAPER_MODE=poll LIVE_PAPER_TICKS=8 LIVE_PAPER_TICK_S=30 \
python scripts/live_paper_trade_coingecko.py
```
