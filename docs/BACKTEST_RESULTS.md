# Source backtest results — what 95 resolved Manifold markets tell us

**Date:** 2026-05-17
**Harness:** `scripts/backtest_sources_xml.py`
**Model:** Gemini `gemini-flash-lite-latest`
**Sample:** 95 resolved binary Manifold markets (200 requested, 95 available)
**Method:** Single bundled XML payload → 4 chunked Gemini calls (≤25 markets each) → one set of per-market per-source adjustments
**Cost:** **$0.012** for the entire sweep
**Artifact:** [`artifacts/sources_brier_20260517T165010Z.json`](../artifacts/sources_brier_20260517T165010Z.json)

---

## Headline numbers

| Forecaster | Brier ↓ | Reliability ↓ | Resolution ↑ | Uncertainty |
|------------|---------|---------------|--------------|-------------|
| **Manifold consensus** | **0.124** | **0.012** | **0.123** | 0.238 |
| Gemini baseline (LLM alone) | 0.237 | 0.046 | 0.049 | 0.238 |

**Murphy decomposition** says Manifold beats raw Gemini on *both* reliability (calibration) and resolution (discrimination). Play-money humans are sharper than the LLM. The LLM is **not** an edge source by itself — it must process the public-data sources to add value.

This is the most important finding of the backtest. Everything else depends on it.

Base rate of YES across the sample: **61.05%.**

---

## Per-source verdicts

| Source | dBrier vs Gemini baseline | Applicability | Verdict | Reasoning |
|--------|----------------------------|---------------|---------|-----------|
| **attention** (Wikipedia) | **−0.0033** | **33.7%** | **ADOPT** | Brier improvement on 1/3 of markets. The most generally applicable source — most questions have an entity with a Wikipedia article. |
| **crowd_sentiment** (Nitter) | **−0.0042** | **41.1%** | **ADOPT** | Best-performing source by margin × applicability. Sentiment is broadly relevant to most markets. |
| orderbook_imbalance (Polymarket L2) | −0.0003 | 8.4% | HOLD | Tiny improvement; well below the 0.002 adoption threshold. Manifold-only sample isn't the right testbed — needs a Polymarket-flavoured corpus. |
| perps_signal (Binance) | −0.0001 | 6.3% | HOLD | Only crypto markets apply; the Manifold sample is too thin. Recommend re-running on a Polymarket crypto-only subset. |
| geopolitical_risk (GDELT) | −0.0004 | 7.4% | HOLD | Below adoption threshold; useful applicability rate suggests value on a geopolitics-biased sample. |
| onchain_tvl (DeFiLlama) | +0.0006 | 6.3% | HOLD | Crypto-specific; sample too thin to judge. |
| lead_lag (TradingView) | +0.0002 | 11.6% | HOLD | Slightly worse than no-source; hold and re-test on ticker-backed markets. |
| basis_arb | −0.0003 | 3.2% | UNTESTABLE | Requires a second venue; circular when Manifold is the only data. |
| consensus_delta | 0 | 0% | UNTESTABLE | Uses Manifold as input; structurally impossible to test against Manifold-resolved markets. |
| cot_positioning (CFTC) | 0 | 4.2% | UNTESTABLE | Sample lacks futures-backed binaries. |
| macro_basis (FRED) | 0 | 4.2% | UNTESTABLE | Sample lacks macro print binaries (CPI/NFP/Fed). |
| macro_release_consensus | −0.0002 | 4.2% | UNTESTABLE | Same as macro_basis — futures release exposure is rare on Manifold. |

---

## What this changes for the project

### 1. Wikipedia + Nitter become primary signal sources

`attention` (Wikipedia pageview velocity) and `crowd_sentiment` (Nitter VADER scorer) are the only two sources that **measurably improved Brier on a held-out sample**. Both are already wired into `apollo.scorer` with ±0.05 caps. Concretely:

- Their oracle-probability contribution caps **should stay at 0.05** — the empirical Brier improvement is small (0.003–0.004) so the bound is the right size.
- We should **wire a Wikipedia attention pull into the Polymarket paper-trade harness** (`scripts/paper_trade_polymarket.py`) so every paper trade includes the live attention z-score.
- Nitter scraping needs reliability work — it's flaky at scale. Consider a 30-min cache + graceful fallback to neutral 0.5 when the source 502s.

### 2. The LLM alone is worse than Manifold

Gemini's solo Brier 0.237 vs Manifold's 0.124 is a **0.113 gap**. This is huge. It means:

- A Boule deliberation that just lets agents argue *without* consuming the new edge sources will likely produce probabilities sharper than raw Gemini but still worse than free Manifold consensus.
- The council's value-add must come from **systematic processing of public-data feeds**, not from "ten LLMs arguing is better than one." Ten LLMs arguing is still ten LLMs.
- This argues strongly for the path already shipped: bound the per-source contribution, force every council member to operate against a real prior (the new `MarketSnapshot` fields), and trust the constitutional gating to refuse trades the council shouldn't take.

### 3. Five sources need a Polymarket-flavoured sample to test

`orderbook_imbalance`, `perps_signal`, `geopolitical_risk`, `onchain_tvl`, `lead_lag` all sit at HOLD with applicability between 6% and 12%. These aren't broken — they're testing on the wrong corpus. Manifold's tail of "Will I clean my room?" markets dilutes the signal.

**Next step:** swap the corpus. When the geo-block on Polymarket Gamma is unblocked (or via a deployed cloud function), pull 200 resolved Polymarket markets and re-run the same harness. The mix there is heavy crypto + politics + sports, which is exactly the regime these five sources are designed for.

### 4. Two sources are structurally untestable here

`basis_arb` and `consensus_delta` can't be tested on Manifold-only data — they require a *different* venue's price as the comparison. This isn't a failure of the source; it's a corpus problem. The right test is "Polymarket implied vs Kalshi implied" or "Polymarket implied vs Manifold consensus" on questions that list on both.

Today these sources sit wired but unvalidated. Their per-feature ±0.05 cap is conservative enough that adopting them defensively is reasonable — they cannot mis-fire by more than 5pp.

### 5. Constitutional + risk plumbing is the actual moat right now

If the LLM is worse than Manifold consensus, and the public-data sources add only ~3 bps Brier improvement each, then **the project's edge today is structural, not informational**:

- Half-Kelly sizing with drawdown haircut (won't blow up)
- Two unilateral vetoes (won't take constitutional-rule breakers)
- Maker rebates + post-only (won't bleed to fees)
- Conformal interval Kelly (won't over-size at the tail extremes)
- Proof of Restraint on-chain (publishes the discipline)

These are real edges of a different kind: not "we know more than the market" but "we lose less to costs and discipline failures than other agents do." That's still alpha — it's just the kind that compounds slowly rather than printing daily.

### 6. The cost of the test was $0.012

This matters operationally: **every source-adoption decision can be re-run for the price of a coffee.** When you collect a Polymarket-flavoured corpus, run it again. When you re-fit calibration after 500 settled trades, run it again. The bundled-XML approach scales — the only constraint is Manifold's tail of weird questions, not LLM tokens.

---

## Concrete code changes implied by this result

1. **Apollo scorer**: no parameter changes needed — the ±0.05 cap is already correctly sized for the empirical improvement.
2. **Paper-trade harness**: pull live Wikipedia attention for each Polymarket market in `scripts/paper_trade_polymarket.py`. Today it doesn't — it only does the toy momentum estimator + size. Live Wikipedia pull = +10 lines.
3. **Crowd-sentiment robustness**: add a 30-min cache + 502 fallback in `services/apollo/src/apollo/sources/nitter.py` so the Nitter signal degrades gracefully.
4. **Polymarket corpus harness**: extend the same XML approach but pull from Polymarket Gamma (when un-geo-blocked) for a 200-market crypto/politics/sports-heavy sample. Test the 5 HOLD sources there.
5. **Constitutional priority**: keep the half-Kelly/drawdown/cap chain as the primary edge, with the two adopted sources as confirmation signal — not standalone size drivers.

---

## What I would do next, ranked

1. **Wire Wikipedia attention into the Polymarket paper harness** (~30 min). Concrete + cheap.
2. **Cache Nitter** (~1 hour). Risk reduction on the second-best source.
3. **Run the XML harness against 200 Polymarket markets** when the geo-block is solved. This is the test that converts 5 HOLDs into ADOPTs or REJECTs.
4. **Re-run this harness after every 100 settled trades** with a 26-week rolling Manifold window. The decision is empirical, not architectural — keep it cheap and recurring.

The pipeline didn't change. The *priority* of which sources to lean on changed. **Wikipedia and Nitter are the two we currently have evidence for.**
