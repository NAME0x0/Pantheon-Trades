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

### 2.2 Reflection round (5th round of debate) ❌
Add a meta-round where Athena evaluates whether the prior round's reasoning held against new information. Cheap: 1 extra LLM call. Increases reliability when signals shift mid-deliberation.

### 2.3 Anti-Goodhart agent diversity metric ❌
Brier-score-driven calibration creates pressure for agents to mimic each other (the agent that copies the median always scores better than the loner). Measure KL-divergence between agent vote distributions over a rolling window; alert when the council collapses to a single voice. Possible mitigation: agent-specific temperature, agent-specific prompts forced to remain distinct.

### 2.4 Multi-LLM consensus for Zeus veto ❌
For the supreme veto specifically, require agreement across two different model providers (e.g. Claude + Gemini). Halves false-positive vetoes; doubles the cost of veto calls. Worth it because veto is the highest-leverage action.

### 2.5 Adversarial selection detection ❌
Flag markets where YOUR order shape exactly matches recent suspicious volume on the same side. Often means a counterparty has information you don't. Build via Polymarket trade-feed analysis.

---

## Tier 3 — Long-term reliability

### 3.1 Reproducibility seed ❌
LLM temperature breaks reproducibility. For audit purposes, optionally pin temperature=0 and pass a stable seed (where the provider supports it). Same signal + same calibration + same prompts → same verdict. Allows deterministic CI regression tests.

### 3.2 Model drift detection ❌
If Anthropic releases Sonnet 4.7 and we silently upgrade, every previous calibrator is now stale. Track the provider's model fingerprint in each completion result; invalidate calibration when fingerprint changes for a significant fraction of training samples.

### 3.3 Live Kalshi connector ❌
Polymarket is geo-restricted in many jurisdictions and charges 2% taker. Kalshi is US-regulated and charges <0.5%. Same binary outcome model. Paper trade Pantheon on both venues in parallel; pick the venue per market based on liquidity + fees.

### 3.4 Event-driven news webhooks ❌
Replace the current RSS polling in Pythia + Brave/GDELT polling in Pythia.news_search with webhook subscriptions to a news vendor (e.g. Newscatcher, Aylien). Real-time matters when markets move on headlines.

### 3.5 Per-trade cost attribution ❌
Today's cost cap is daily-cumulative. Better: attribute each LLM call to a (signal_id, agent, round) tuple so we can answer "this trade cost $0.42 of LLM and $0.0001 of gas; was the expected edge worth it before placing?"

### 3.6 Reflection-driven prompt evolution ❌
After each settled trade, run an Ostrakon pass that asks: "what would have changed the council's verdict?" Use the response to suggest prompt edits per agent. Human reviews and applies. Genuine learning loop.

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
