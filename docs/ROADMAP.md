# Pantheon Trades — Mission-Critical Roadmap

This document captures the work that takes the system from
"infrastructure-grade, alpha-unproven" to "actually capable of
preserving capital in production." Items are ranked by impact on
profitability and survival, not by ease of implementation.

Status legend:

- ✅ **Done** — shipped in `main`
- 🔄 **In progress** — partially wired
- ❌ **Not started**

---

## Tier 1 — Survival (must-have before any live execution)

### 1.1 Slippage + fee modeling ✅
Live-quality fill simulation in the paper book: half-spread cost, slippage vs depth, configurable Polymarket-style taker fee (default 2%), max-take-fraction cap with partial-fill flagging. Without this, paper PnL is fantasy.

### 1.2 Circuit breaker on consecutive losses ✅
After `STRATEGOS_MAX_CONSECUTIVE_LOSSES` losing settlements (default 3), live mode auto-flips back to paper. Counter lives in Redis so multiple workers see the same view. Resets on the first winning settlement.

### 1.3 First-N manual approval ✅
The first `STRATEGOS_REQUIRE_MANUAL_FIRST_N` live trades (default 5) require `STRATEGOS_LIVE_APPROVED=1` in the environment. Prevents accidental live mode on a fresh deploy.

### 1.4 Daily cost cap ✅
Cumulative LLM + chain + fee spend tracked in Redis (`strategos:cost:usd:day:YYYY-MM-DD`). Crossing `STRATEGOS_DAILY_COST_CAP_USD` (default $25) halts live execution for the remainder of the UTC day.

### 1.5 Quote-time edge re-check ✅
Before any live submission, re-evaluate the market's current ask vs the Apollo signal's recorded ask. If drift exceeds `STRATEGOS_MAX_QUOTE_DRIFT` (default 3pp), abort and emit a Proof-of-Restraint candidate.

### 1.6 Recursive calibration loop ✅
`ostrakon recalibrate-loop` daemon listens to `strategos:resolutions`, after every `N` new settlements (default 5) re-fits per-agent calibration and atomically swaps `agent_calibrations.json`. Next Boule deliberation picks up the new numbers without restart.

### 1.7 Historical data bootstrap ✅
`tests/bootstrap_historical_data.py` populates `.cache/polymarket_resolved.jsonl` from three sources (Polymarket Subgraph, Polymarket gamma-api, Manifold Markets) so backtest harness has data to chew through even when CLOB is geo-blocked.

---

## Tier 2 — Profitability (between "doesn't lose" and "actually makes money")

### 2.1 Apollo signal redesign ❌
The current 7-dimension scoring is heuristic (liquidity, catalyst, sentiment, etc.) — those are *quality* features, not *prediction* features. Real predictive features to add:

- **Order-book imbalance** — depth-weighted bid/ask asymmetry over the last N minutes
- **Lead/lag with related markets** — when a correlated market moves, this one usually follows within hours
- **Cross-venue arbitrage** — Polymarket vs Kalshi vs Manifold on the same underlying
- **Sentiment velocity** — not absolute polarity, but the time-derivative
- **News-NER entity matching** — connect breaking news to a specific market via named-entity resolution

This is where alpha actually lives. Plan: 2-3 weeks of feature engineering work; A/B test each new feature against a hold-out.

### 2.2 Reflection round (5th round of debate) ✅
Athena re-evaluates the round-4 verdict against the full debate. Returns HOLD or RECONSIDER plus a confidence delta in [-0.10, +0.10] which is applied to weighted_approval *before* the approval threshold check. Gated by ``BOULE_REFLECTION_ENABLED`` (default on). One extra LLM call per deliberation; cheap and catches reasoning inconsistencies.

### 2.3 Anti-Goodhart agent diversity metric ✅
``boule.diversity.measure`` computes Shannon entropy + probability-estimate std into a composite ∈ [0, 1]. Emitted as a ``diversity`` trace event after every round-4 tally; alerts below ``MIN_DIVERSITY`` (0.35). Olympus can subscribe and rotate prompts / temperatures when the council collapses.

### 2.4 Multi-LLM consensus for Zeus veto ✅
``BOULE_ZEUS_CONSENSUS_PROVIDER=<gemini|openai|...>`` triggers an independent confirmation call after a Zeus REJECT. The veto only sticks when the secondary provider also flags it. Fails closed (keep the veto) on error so we always err on the side of not trading. Halves false-positive vetoes at the cost of one extra LLM call per veto.

### 2.5 Adversarial selection detection ❌
Flag markets where YOUR order shape exactly matches recent suspicious volume on the same side. Often means a counterparty has information you don't. Build via Polymarket trade-feed analysis.

---

## Tier 3 — Long-term reliability

### 3.1 Reproducibility seed ✅
``BOULE_LLM_DETERMINISTIC=1`` pins temperature=0 across all three adapter families (OpenAI-compat, Gemini, Anthropic), plus a ``BOULE_LLM_SEED`` (default 42) where the provider supports it. Same signal + same calibration + same prompts → same verdict, ready for CI regression tests.

### 3.2 Model drift detection ✅
``boule.telemetry.DriftTracker`` records the provider model fingerprint on every completion (e.g. ``anthropic/claude-sonnet-4-6``, ``google/gemini-2.5-flash-lite``). Sliding window of ``BOULE_DRIFT_WINDOW`` (default 200); when mismatch exceeds ``BOULE_DRIFT_FRACTION`` (default 20%) a ``model_drift`` trace event fires. Calibration should be refit after every drift event.

### 3.3 Live Kalshi connector ❌
Polymarket is geo-restricted in many jurisdictions and charges 2% taker. Kalshi is US-regulated and charges <0.5%. Same binary outcome model. Paper trade Pantheon on both venues in parallel; pick the venue per market based on liquidity + fees.

### 3.4 Event-driven news webhooks ❌
Replace the current RSS polling in Pythia + Brave/GDELT polling in Pythia.news_search with webhook subscriptions to a news vendor (e.g. Newscatcher, Aylien). Real-time matters when markets move on headlines.

### 3.5 Per-trade cost attribution ✅
``boule.telemetry.CostLedger`` records (thesis_id, signal_id, agent, round, provider, model, tokens_in, tokens_out, usd, timestamp) on every LLM call. Pricing table covers Anthropic, Gemini, OpenAI, DeepSeek, xAI, Groq Llama; unknown models fall back to a conservative $1/1M-tokens default. ``ledger.per_thesis_breakdown(thesis_id)`` answers "how much LLM did this trade cost, broken down by agent?"

### 3.6 Reflection-driven prompt evolution ❌
After each settled trade, run an Underworld pass that asks: "what prompt edit would have changed the council's verdict?" Save the suggestion to disk; human reviews and applies. Real learning loop.

---

## Tier 4 — Data + robustness primitives (newly added)

### 4.1 CoinGecko live-price client ✅
``services/pythia/src/pythia/coingecko.py`` — async client with min-spacing rate limiter (free 30 RPM), disk cache (60s spot, 300s historical TTLs), demo + pro-key auto-detection. Exposes ``spot(symbols)`` returning ``SpotPrice`` (usd, 24h vol, 24h change, updated_at) and ``history(symbol, days)`` returning ``PriceSeries`` whose ``closes()`` plugs into Apollo's lead/lag feature.

### 4.2 Bloomberg Terminal OSS alternatives ✅
``services/pythia/src/pythia/openbb_adapter.py`` — direct REST calls to the same upstream sources OpenBB Terminal pulls from, without the 200 MB SDK dep. Covers:
  - Equity OHLC via Stooq (free, no key)
  - FRED macro series via the no-key CSV endpoint
  - Optional ``yfinance`` bridge wrapped in ``asyncio.to_thread``

### 4.3 Correlation-aware portfolio sizing ❌
Today's half-Kelly ignores correlation between open positions. Two correlated long bets = 2× effective exposure. Pull pairwise correlation across open trades and downsize each new bet by ``(1 - max_corr_with_open)``.

### 4.4 Drawdown-adjusted Kelly fraction ❌
When down ``X%`` on the week, scale Kelly by ``(1 - X)``. Smooths the risk envelope, prevents pyramiding losses.

### 4.5 Resolution-lag state in Argos ❌
Polymarket markets resolve hours-to-days after the underlying event. Add a ``pending_resolution`` state with a configurable TTL; trades parked there don't count toward exposure caps but stay visible.

### 4.6 Agent ablation testing ❌
Run the council with one agent removed across a backtest; measure delta-Brier. Quantifies each agent's actual contribution. Agents whose removal *improves* Brier should be retired by Moirai.

### 4.7 Walk-forward windowed calibration ❌
``ostrakon calibrate`` today uses all history equally. Better: fit Platt + isotonic on 30 / 90 / 180-day rolling windows, weight recent more, alert when the windows disagree.

### 4.8 News-NER market matching ❌
When a breaking-news entity matches an open market keyword, fast-track that signal — bypass the normal cron cadence.

### 4.9 Two-stage approval ❌
After Areopagus says PROCEED, sleep 60s and re-check market state. The Tier 1 quote-drift gate is a subset of this — two-stage is the general form.

### 4.10 Pseudo-order liquidity probing ❌
Submit + immediately cancel a small order to estimate true depth before sizing. Paper-only safety initially.

---

## What the loop looks like end-to-end (post Tier 1)

```
Chronos cron tick (every 5 min)
      ↓
Apollo scans Polymarket → 1-N scored signals
      ↓
Boule deliberates each signal (10 agents, 4 rounds, cached LLM calls)
      ↓
Boule applies fresh agent_calibrations.json before tally
      ↓
Areopagus gates (constitutional caps + half-Kelly)
      ↓
   approved ── SafetyWrapper.guard() ─── PROCEED ─→ Strategos lives
       │           │                       ↑
       │           ├─ CIRCUIT_BREAKER  ────┤
       │           ├─ COST_CAP         ────┤
       │           ├─ AWAIT_MANUAL     ────┤
       │           └─ QUOTE_DRIFT      ────┘ all → paper fallback +
       │                                       Proof of Restraint
       │
   rejected ─→ ProofOfRestraint witness on Arc Testnet
      ↓
Strategos settles or Argos exits
      ↓
Ostrakon scores each agent's prediction → Brier update
      ↓
Ostrakon recalibrate-loop: every 5 settlements,
   refit per-agent Platt + isotonic, swap JSON atomically
      ↓
Next deliberation picks up the new calibration. Loop closes.
```

This is the system as currently shipped. Tier 2 + 3 take it from "closed loop" to "closed loop that actually finds alpha." Tier 1 is the bare minimum to ship without losing capital catastrophically.
