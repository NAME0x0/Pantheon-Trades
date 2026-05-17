# Fees, calibrations, and unconsidered data — research notes

The CoinGecko paper-trade artifact ([`artifacts/coingecko_paper_*.json`](../artifacts/))
shows the brutal truth: naive momentum on real BTC bars loses 39.5%
because fees + slippage eat the edge. This document compiles
*proven*, *popular*, *open-source-compatible* ways to fix that, with
real numbers, real sources, and concrete wiring points in this repo.

Three sections:

1. **[Reducing fees](#1-reducing-fees)** — Polymarket CLOB v2, maker
   rebates, post-only flag, batch auctions, pUSD migration.
2. **[Proven calibrations](#2-proven-calibrations)** — beta calibration,
   conformal prediction, temperature scaling, Brier decomposition.
3. **[Unconsidered data sources](#3-unconsidered-data-sources)** — GDELT
   2.0, FRED, SEC EDGAR, Wikipedia pageviews, cross-market
   aggregators, others.

---

## 1. Reducing fees

### Polymarket fee structure (post Fee Structure V2, March 30 2026)

Polymarket pivoted from zero fees to a **taker-only** fee model on
March 30, 2026, with the rates below ([source][pm-fees]):

| Category | Taker fee | Peak $/100 shares at p=0.50 |
|----------|-----------|-----------------------------|
| Crypto | 7.20% nominal* | $1.80 |
| Sports | 3.00% nominal | $0.75 |
| Finance · Politics · Mentions · Tech | 4.00% nominal | $1.00 |
| Economics · Culture · Weather · Other | 5.00% nominal | $1.25 |
| Geopolitics · World events | **0%** | $0.00 |

\* "Nominal" here is the Polymarket-published rate which scales with the
contract price away from $0.50 — actual realised fee is bounded by the
$/100 column. Math at the [fee calculator][pm-feecalc].

Critically: **makers pay 0%** ([source][pm-help-fees]).

### Polymarket Maker Rebates Program

Launched alongside the taker fee. The protocol takes 20–25% of each
collected fee and **redistributes it daily in USDC** to liquidity
providers ([source][pm-rebates]). Top makers report **5–20% annualised
on deployed capital** in rewarded markets ([source][nyc-mm-guide]).

| Mechanism | Detail |
|-----------|--------|
| Eligibility | Any limit order that rests on the book before being taken. |
| Payout cadence | Daily, in USDC to your trading wallet. |
| Minimum payout | $1 USDC accrued. |
| Weighting | Volume-weighted *or* fee-curve weighted depending on market phase. |
| Flag | `post-only` on the order ensures it never crosses (else rejected). |

### Polymarket CLOB v2 (April 28 2026)

Launched 19 days ago as of this writing ([source][pm-clob-v2]):

- **EIP-712 Exchange domain version** bumped from "1" to "2". V1
  signatures will not work post-cutover.
- **New `pUSD` ERC-20 collateral** — 1:1 USDC-backed, on-chain
  enforcement. Trades settle in `pUSD` not `USDC`.
- **$1M liquidity rewards** program ran in the first 24h —
  $500k in the first 2 hours, $500k spread across the rest of the
  day. *That window is closed*, but the rewards-on-rebates structure
  remains.
- **Python v2 client** at [`Polymarket/py-clob-client-v2`][py-clob-v2]
  and Rust at [`rs-clob-client-v2`][rs-clob-v2].

### US-regulated Polymarket exchange

Separate venue, separate fee table ([source][bitget-fees]):

- **0.30% taker fee**
- **0.20% maker rebate** (paid to LPs)
- No fee-tier complexity — flat across categories.

### What this repo should do

| Change | Where | Expected impact |
|--------|-------|-----------------|
| Migrate to py-clob-client-v2 | `services/strategos/src/strategos/polymarket_clob.py` | Future-proof; v1 sigs stop validating. |
| Default to `post-only` for non-urgent | `services/strategos/src/strategos/execution_mode.py` (extend `ExecutionDecision`) | Switches from –7% net trip to +rebate net trip on patient orders. |
| Track and book maker rebates | New `services/strategos/src/strategos/maker_rebate.py` | Accurate net-PnL accounting; surface to Ostrakon. |
| Add geopolitics category preference | `apollo.scorer` already has category-weighting; bias the band scorer toward 0-fee categories. | Free trades when edge present. |
| Migrate USDC → pUSD on settlement | `services/parthenon/`, `services/areopagus/chain.py` | Required for any live execution after v2 cutover. |

For a maker-driven trade, the **edge floor** drops from ≈4% (2×2% taker
roundtrip) to ≈ **+0.4% maker-rebate inflow** assuming 20% of nominal
4% fee rebated to maker on both legs. That is the difference between
"impossible to make money on small edges" and "every small edge that
clears slippage prints."

---

## 2. Proven calibrations

The system already ships **Platt scaling + isotonic regression**
([`services/ostrakon/src/ostrakon/agent_calibration.py`](../services/ostrakon/src/ostrakon/agent_calibration.py)).
Three additions are widely benchmarked as superior on specific data
regimes:

### Beta calibration (Kull, Silva-Filho, Flach 2017)

**What:** parametric calibration that fits the calibration curve to a
ratio of two beta distributions, not a sigmoid. Two-parameter family
(a, b) plus an intercept c ([source][trainindata-cal]; [paper][beta-paper]).

**Why it beats Platt:**
- Beta family **contains the identity** as a special case (a=b=1). If
  the model is already calibrated, beta calibration leaves it alone.
  Platt scaling *cannot* express the identity and will distort a
  well-calibrated model.
- Two extra parameters vs Platt's two — small overfit risk.
- Smooth (unlike isotonic which is piecewise-constant), so per-call
  derivatives are stable for downstream Kelly sizing.

**When to use:** small-to-medium calibration sets (200 – 5000 settled
trades). Above 10k, isotonic catches up.

**Implementation:** four lines after sklearn imports — fit a logistic
on `[log(s), log(1-s)]` features. Pythonic stub in this repo's
[`services/ostrakon/src/ostrakon/beta_calibration.py`](../services/ostrakon/src/ostrakon/beta_calibration.py)
(added in the same commit as this doc).

### Conformal prediction

**What:** distribution-free framework that converts any base
classifier into a calibrated *interval* predictor with finite-sample
coverage guarantees ([source][cp-wiki], [arxiv][cp-arxiv]).

**Why it's interesting for Pantheon:**
- Sized positions need *probability intervals*, not point estimates.
  Conformal gives the 95% interval directly: `[p_lower, p_upper]`.
- Kelly sizing is highly sensitive to overconfidence at the
  near-certain extremes (p ≈ 0.95 vs 0.99 is the difference between
  doubling your stake). Conformal naturally regularises by widening
  the interval where calibration data is thin.
- The split-conformal variant takes ~50 lines of code. No retraining
  needed.

**Why it's *not* a silver bullet:**
- Coverage guarantee assumes exchangeable data — prediction-market
  outcomes are not exchangeable across regime changes (election cycles,
  bull/bear macro). Use the *adaptive* variant (rolling-window
  conformal; [arxiv][cp-adaptive]) which reweights calibration data.

**Wiring point:** wrap whatever council probability lands in
`pantheon_core.schema.Thesis.council_probability` into a `[p_lo, p_hi]`
interval. Areopagus then sizes against `p_lo` (conservative) rather
than the point estimate.

### Temperature scaling (Guo et al 2017)

**What:** the simplest possible calibration — single scalar T that
divides the model's logit before the sigmoid. Used in modern LLM
output calibration and ImageNet ([source][trainindata-platt]).

**Why it matters here:** if a council is well-shaped but consistently
overconfident, one parameter fixes it. Cheap, stable, robust to
overfitting on small data. Should be the *default* unless the
miscalibration is shape-distorted (use isotonic) or in the tail
(use beta).

### Brier-decomposition-driven optimisation

The Brier score decomposes into **Reliability − Resolution +
Uncertainty** ([source][brier-wiki]):

- **Reliability** is what calibration improves. Already shipped.
- **Resolution** is what *feature engineering* and *better data*
  improves — it measures how well the model separates high-from-low
  outcome bins.
- **Uncertainty** is irreducible — set by the actual outcome rate.

If your overall Brier is bad, decompose first. If reliability is the
problem, calibrate harder. If resolution is the problem, calibration
is a band-aid — you need a sharper signal. Pantheon's Brier-by-agent
calculator (`ostrakon`) should surface this decomposition.

### Wiring summary

| Method | Best regime | Effort | Code stub |
|--------|------------|--------|-----------|
| Platt (sigmoid) | < 200 samples, near-sigmoid miscalibration | shipped | `agent_calibration.py` |
| Isotonic | > 5000 samples, complex miscalibration | shipped | `agent_calibration.py` |
| Beta | 200 – 5000 samples; already-calibrated regions | **new in this commit** | `beta_calibration.py` |
| Temperature | One-shot, post-hoc fix | small | `agent_calibration.py` (one extra method) |
| Conformal | Want intervals, not just points | medium | TBD — `conformal_calibration.py` |

---

## 3. Unconsidered data sources

[`docs/EDGE_SOURCES.md`](EDGE_SOURCES.md) lists 10 sources. Here are
six more, picked because each one is **free**, **public-data**, and
**academically validated** for predictive signal.

### a. GDELT 2.0 — global events, 15-minute cadence

**What.** Real-time catalogue of news events from print + broadcast +
web across 100+ languages, going back to 1979 ([source][gdelt]).
Updates every 15 minutes. Full dataset queryable on **Google BigQuery
with 1TB/month free** ([source][gdelt-bq]).

**Why it's relevant.** A 2025 arxiv paper applied GDELT + FinBERT to FX
trading and reported out-of-sample **Sharpe 5.87 EUR/USD, 4.65 USD/JPY,
4.65 Treasuries, CAGR >50% in FX** over the backtest period
([paper][gdelt-alpha]). That is in a regime where everyone has access
to the same data, suggesting the *extraction* (NLP pipeline + event
typing + tone weighting) is where edge lives.

**Wiring.** New module `services/pythia/src/pythia/gdelt.py` (shipped
in the same commit as this doc as a skeleton). DOC API gives
near-real-time without BigQuery. Apollo feature
`geopolitical_risk_score` joins GDELT tone deltas to political /
geopolitical Polymarket markets.

### b. Wikipedia pageviews — investor attention proxy

**What.** Per-article, per-hour pageview counts dating back to 2008
([source][wiki-pv]). Free, no key, REST API.

**Why proven.** Multiple peer-reviewed papers show Wikipedia pageviews
of a company / candidate / event predict subsequent market moves
([source][wiki-attention]). The mechanism: spikes in lay attention
precede catalysts. For prediction markets where the *underlying
question* is in a Wikipedia article (elections, court rulings, sports
finals, central-bank decisions), pageview velocity is a leading
indicator.

**Wiring.** `services/pythia/src/pythia/wikipedia.py` — fetch hourly
pageviews for an entity. Apollo feature: `attention_velocity_z`. Apply
to politics + sports + science markets.

### c. SEC EDGAR — institutional positioning

**What.** Public filings: 13F (quarterly institutional holdings),
Form 4 (insider transactions), 8-K (material events) ([source][edgar]).
Free API, no key.

**Why relevant for prediction markets.** When 13F filings show large
funds rotating into / out of equity exposure for a specific catalyst
(election, M&A, regulatory decision), the same catalyst usually has a
Polymarket binary. The basis between "institutional positioning
direction" and "binary market direction" is a documented
proto-signal — see also Quiver's CongressionalTrading dataset.

**Wiring.** `services/pythia/src/pythia/edgar.py`. Apollo feature:
`institutional_positioning_signal`.

### d. FRED economic series — macro context

**What.** Federal Reserve Bank of St. Louis maintains **816,000+
economic time series**, all free, REST API ([source][fred]).

**Why obvious-in-hindsight.** Polymarket has explicit binaries on
*every Fed rate decision*, *every CPI release*, *every NFP print*. The
forward indicators FRED publishes (initial jobless claims, ISM,
Michigan sentiment, breakeven inflation) are leading indicators of the
release the market is pricing. Combining them with the binary's
implied probability gives a basis to trade.

**Wiring.** `services/pythia/src/pythia/fred.py` (no API key required
for most endpoints). Apollo feature: `macro_release_basis_score`.

### e. Cross-aggregator basis (Arbitix-style)

**What.** Cross-platform probability aggregator. **Arbitix** combines
Polymarket + Kalshi probabilities live with a 5-minute free tier
([source][arbitix]). The **AGI Timelines Dashboard** aggregates
Metaculus + Manifold + Kalshi for AI-related questions
([source][agi-dash]).

**Why valuable.** When the same question trades at different
implied probabilities on different venues, the basis is *literal*
arbitrage if the resolution mechanism is the same. When it isn't, the
basis is still a calibration signal: which venue is sharper for this
question class?

**Wiring.** `services/pythia/src/pythia/aggregator.py`. New Apollo
feature: `cross_venue_basis_z`. Areopagus already has cross-venue
exposure caps so no new constitution rules needed.

### f. Manifold Markets — research-friendly free API

**What.** Manifold is a play-money prediction market with generous
free API limits and CC-BY-SA data ([source][manifold]). 30k+ markets
spanning the same question taxonomy as Polymarket.

**Why useful even though it's play-money.** The *consensus* of a
Manifold market is a free real-time prediction by humans who don't pay
fees. If the Polymarket implied probability deviates significantly
from the Manifold consensus on the same question, the gap is either
the fee structure or actual edge.

**Wiring.** Same `aggregator.py` module — Manifold goes alongside
Arbitix. Apollo feature: `manifold_consensus_delta`.

### g. The Awesome list

[`Awesome-Prediction-Market-Tools`][awesome] is a curated list of
APIs / agents / dashboards / copy-trading tools. Re-check quarterly
for new entries.

---

## Concrete order of operations (what to ship next, ranked)

1. **Wire `post-only` flag through Strategos** so all council-approved
   non-urgent trades default to maker mode. (~50 lines.) Immediate
   fee delta: –4% per round-trip → +rebate per round-trip.
2. **Beta calibration** as an alternative to Platt
   (shipped this commit). Run an ablation: refit on the last 90
   days of settled trades using Platt vs Beta vs Isotonic. Adopt
   whichever has lowest reliability term in the Brier decomposition.
3. **GDELT pythia source** (shipped this commit as skeleton). First
   real Apollo feature using it: politics + geopolitics markets.
4. **Migrate to py-clob-client-v2** + pUSD. Hard requirement for any
   live execution after the V1 cutover.
5. **Wikipedia pageviews + FRED + EDGAR** sources. Order doesn't
   matter; each takes ~100 lines of code + an Apollo feature.
6. **Conformal interval** wrapper around `council_probability`. Pipe
   `p_lo` into Areopagus sizing.

---

## What this list does **not** assume

- It does **not** assume any private alpha.
- It does **not** assume the council is currently calibrated.
  Validate with `ostrakon ablate` first.
- It does **not** assume Polymarket fee structure stays at V2 — they
  have changed it three times in the past year. Recheck quarterly.
- It does **not** include paid-vendor data (Bloomberg, Refinitiv,
  Coinglass paid tier). Everything above is free or has a free tier.

---

## Sources

[pm-fees]: https://www.predictionhunt.com/blog/polymarket-fees-complete-guide
[pm-feecalc]: https://www.tradetheoutcome.com/polymarket-fees/
[pm-help-fees]: https://help.polymarket.com/en/articles/13364478-trading-fees
[pm-rebates]: https://docs.polymarket.com/polymarket-learn/trading/maker-rebates-program
[pm-clob-v2]: https://www.cryptotimes.io/2026/04/28/polymarkets-clob-v2-goes-live-with-1m-rewards-new-pusd-token/
[py-clob-v2]: https://github.com/Polymarket/py-clob-client-v2
[rs-clob-v2]: https://github.com/Polymarket/rs-clob-client-v2
[bitget-fees]: https://web3.bitget.com/en/academy/polymarket-fees-explained-how-taker-fees-rebates-and-trading-costs-work
[nyc-mm-guide]: https://newyorkcityservers.com/blog/prediction-market-making-guide
[trainindata-cal]: https://www.blog.trainindata.com/probability-calibration-in-machine-learning/
[trainindata-platt]: https://www.blog.trainindata.com/complete-guide-to-platt-scaling/
[beta-paper]: https://www.abzu.ai/data-science/calibration-introduction-part-2/
[cp-wiki]: https://en.wikipedia.org/wiki/Conformal_prediction
[cp-arxiv]: https://arxiv.org/html/2512.17048v1
[cp-adaptive]: https://arxiv.org/html/2511.13608v1
[brier-wiki]: https://en.wikipedia.org/wiki/Brier_score
[gdelt]: https://www.gdeltproject.org/
[gdelt-bq]: https://console.cloud.google.com/marketplace/product/the-gdelt-project/gdelt-2-events
[gdelt-alpha]: https://arxiv.org/html/2505.16136v1
[wiki-pv]: https://wikitech.wikimedia.org/wiki/Analytics/AQS/Pageviews
[wiki-attention]: https://onlinelibrary.wiley.com/doi/full/10.1002/isaf.1508
[edgar]: https://www.sec.gov/edgar/sec-api-documentation
[fred]: https://fred.stlouisfed.org/docs/api/fred/
[arbitix]: https://arbitix.io/
[agi-dash]: https://agi.goodheartlabs.com/
[manifold]: https://docs.manifold.markets/api
[awesome]: https://github.com/aarora4/Awesome-Prediction-Market-Tools
