# Edge sources — proven, public, and (mostly) free

Pantheon Trades is glass-box on *risk discipline*. It does **not** ship
with a proven alpha source out of the box, and the CoinGecko paper-trade
artifact ([`artifacts/coingecko_paper_*.json`](../artifacts/)) is honest
about that: 79 trades on naïve BTC tick momentum lose 39.5% to fees and
slippage. The pipeline is real; the edge is what you have to bring.

This document catalogues edge sources that have a public-data foothold
and a defensible mechanism. None of these are guaranteed to print money
— if they were, the public-data version would be arbitraged out. Each
entry below gives:

- **Mechanism** — *why* there is plausibly an edge for a careful trader.
- **Data source** — exact endpoint or library, with licence.
- **Wiring point** — where in this repo the source would land.
- **Falsification** — the cheapest, fastest way to find out the edge
  isn't real for *you*.

The list is ordered by signal-to-noise observed in academic / public
backtests, descending. Take that ordering as a starting hypothesis, not
a recommendation.

---

## 1. Cross-venue basis arbitrage (Polymarket ↔ Kalshi ↔ sportsbooks)

**Mechanism.** Polymarket, Kalshi, and conventional sportsbooks list
overlapping events: election outcomes, Federal Reserve rate decisions,
weather, sports finals. Their order books drift apart for the same
real-world question. The spread *after* fees and gas is the edge.

**Data source.**
- Polymarket CLOB — public REST + WebSocket. See
  [`services/strategos/src/strategos/polymarket_clob.py`](../services/strategos/src/strategos/polymarket_clob.py).
- Kalshi REST — public on free tier, $0/mo for read-only. Already wired
  at [`services/pythia/src/pythia/kalshi.py`](../services/pythia/src/pythia/kalshi.py).
  Cents-denominated; we normalise to unit prices.
- Sportsbook consensus odds via [The Odds API](https://the-odds-api.com)
  free tier (500 req/mo). Licence: paid for commercial volume.

**Wiring point.** A new feature in
`services/apollo/src/apollo/features/basis_arb.py` that for each
(question_id, resolution_date) tuple computes
`spread = polymarket_yes - kalshi_yes` (or the sportsbook implied prob)
and surfaces signals where `|spread| > fees + slippage_budget`.

**Falsification.** Pull 90 days of resolved election + Fed markets from
both venues; compute realised spreads; subtract 4% round-trip fees; if
the residual is < 1.5% mean per trade with positive skew, *there is no
edge after costs.* Most of the time, there isn't — until there is.

---

## 2. Election poll consensus (RCP + 538 + state-level Marist)

**Mechanism.** Polymarket election markets persistently mispricing
state-level outcomes vs the aggregate of state polls. The systematic
bias is documented in academic work: markets overweight the most recent
poll, underweight the consensus.

**Data source.**
- [RealClearPolitics aggregates](https://www.realclearpolitics.com/)
  — public HTML scrape; no commercial API.
- [538 (FiveThirtyEight)](https://github.com/fivethirtyeight/data)
  open data on GitHub, CC-BY 4.0 historically (post-2024 ownership
  transition has shifted hosting; check current licence).
- State polls via [Wikipedia's election aggregator pages](https://en.wikipedia.org/wiki/2028_United_States_presidential_election)
  — Wikidata-linked, CC-BY-SA.

**Wiring point.** Lives naturally in Apollo features. Reuse the
existing news-NER plumbing at
[`services/apollo/src/apollo/features/news_ner.py`](../services/apollo/src/apollo/features/news_ner.py)
to match state names → Polymarket markets.

**Falsification.** Bin all resolved 2020 + 2024 + 2028-primary
state-level markets by `consensus_poll - market_implied_prob`. If the
top quintile (largest disagreement) doesn't show realised PnL > 5% net
of fees, the edge is gone. Already-public papers suggest it's there but
narrow; trade size matters.

---

## 3. CFTC commitments-of-traders (CoT) reports

**Mechanism.** Each Tuesday the CFTC releases positioning of large
commercial and speculative traders in futures markets. The
*commercial-net* against *speculator-net* is a well-documented
mean-reversion signal at multi-month horizons. Polymarket has growing
"will X commodity be above Y by Z" markets. The CoT data is direct
input.

**Data source.** [CFTC Public Reporting Environment](https://publicreporting.cftc.gov/)
— public REST API, no key required. Updated weekly Friday afternoon
for Tuesday data.

**Wiring point.** Extend Pythia: `services/pythia/src/pythia/cftc.py`
following the Kalshi pattern. Apollo feature: a commodity-specific
positioning score per market.

**Falsification.** Aggregate WTI / gold / wheat / S&P futures CoT for
2015-2025; align with realised front-month price; check Spearman rank
correlation of commercial-net at +90 days vs realised front-month
return. If `|ρ|` < 0.10, the public signal is too noisy.

---

## 4. Open-interest skew + funding rates (crypto)

**Mechanism.** Perpetual-futures funding rates and open-interest skew
on Binance / Bybit / Deribit are leading indicators of forced
liquidations on crypto. Polymarket has "BTC > $X by date" binary
markets that are sensitive to short-term liquidation cascades.

**Data source.**
- [Coinglass](https://www.coinglass.com/) — open-interest + funding.
  Free tier exists; commercial volume requires a paid key.
- [Binance public REST](https://binance-docs.github.io/apidocs/futures/en/)
  — `/fapi/v1/fundingRate`, `/fapi/v1/openInterest`. No auth required.
- [Bybit v5 API](https://bybit-exchange.github.io/docs/v5/intro) — same.

**Wiring point.** Pythia: `services/pythia/src/pythia/perps.py`.
Compute `funding_z = (funding - rolling_mean) / rolling_std`. When
extreme, surfaces a tail-risk flag to Cassandra and a sizing input to
Areopagus.

**Falsification.** Backtest: when funding-z > +2σ for 8h+, does BTC
realise negative returns over the next 24h with > 55% frequency? If
no, the signal is consumed.

---

## 5. NOAA / ECMWF weather (for weather + commodity markets)

**Mechanism.** Kalshi lists weather binaries ("will NYC see > 80°F on
date X"). The market-implied probability often diverges from the
ensemble mean of public models. Trader edge: a sharper read on the
ensemble than the consensus implied price.

**Data source.**
- [NOAA NDFD REST](https://digital.weather.gov/) — US weather, fully
  public, no key.
- [ECMWF Open Data](https://www.ecmwf.int/en/forecasts/datasets/open-data)
  — global, public since 2022. CC-BY 4.0.
- [Open-Meteo](https://open-meteo.com/) — aggregator, free tier 10k
  calls/day. MIT-licensed clients.

**Wiring point.** Pythia: `services/pythia/src/pythia/weather.py`.
Apollo feature joins (market_lat, market_lon, market_date) to the
ensemble forecast and computes probability-of-threshold.

**Falsification.** For 12 months of resolved Kalshi weather markets,
compare `market_implied_prob` to `ensemble_mean_prob`. If realised
outcomes don't track ensemble closer than the market, the public
ensemble is already priced in.

---

## 6. Congressional disclosures + insider trading (PoliticalShares-style)

**Mechanism.** US House and Senate periodic-transaction reports (PTRs)
disclose member trades 30-45 days after the fact. Several academic
papers show Senate trades modestly outperform the index in a 30-day
forward window. Polymarket has "will member X resign / win / lose"
markets that are sensitive to public PTR filings (gift-disclosure
scandals especially).

**Data source.**
- [Quiver Quantitative](https://www.quiverquant.com/) — Congressional
  PTRs, scraped + structured. Free tier reads, paid for bulk. ToS
  permits research use.
- [House Clerk PTR PDFs](https://disclosures-clerk.house.gov/) — raw,
  public, free, painful to parse.

**Wiring point.** Apollo: `services/apollo/src/apollo/features/congress_ptr.py`.
A flag-style feature, not a probability — primarily for Cassandra and
Themis to surface to the council.

**Falsification.** Backtest: do congressional disclosures correlate
with subsequent re-election-market moves > 24h after publication? If
< 2pp, the disclosure is already absorbed at filing.

---

## 7. On-chain treasury flows (DeFiLlama TVL deltas + stablecoin mints)

**Mechanism.** Large stablecoin mints (Tether, USDC, USDT) historically
precede crypto rallies by 1-3 days, especially on Sundays / illiquid
windows. TVL inflows into specific protocols correlate with token
performance over 7-14 days. Polymarket has crypto-binary markets that
are sensitive to these flows.

**Data source.** [DeFiLlama public API](https://defillama.com/docs/api)
— free, no key, CC-BY 4.0 attribution.
Already wired at [`services/pythia/src/pythia/defillama.py`](../services/pythia/src/pythia/defillama.py).
Stablecoin marketcap deltas + chain-TVL deltas are first-class.

**Wiring point.** Already shipped. Apollo feature in
[`services/apollo/src/apollo/features/onchain_tvl.py`](../services/apollo/src/apollo/features/onchain_tvl.py)
needs extension to compute *delta* over rolling windows, not just
absolute levels.

**Falsification.** For 2 years of resolved BTC + ETH price-target
Polymarket markets, regress realised resolution against
`stablecoin_mcap_delta_7d` lagged. If `R²` < 0.05, the signal is gone
or your lag is wrong.

---

## 8. Social-velocity sentiment (Nitter RSS + Reddit)

**Mechanism.** Velocity of mentions (first-derivative of post counts)
on niche subreddits and politics-Twitter precedes spot moves more
reliably than absolute mention counts. Already a known retail-flow
proxy.

**Data source.**
- Nitter RSS scraping. Already wired in
  [`services/apollo/src/apollo/sources/nitter.py`](../services/apollo/src/apollo/sources/nitter.py)
  with the in-tree VADER-style sentiment scorer.
- Reddit public JSON (`*.json` suffix on any Reddit URL) — no auth
  needed for read; rate-limited to 60 req/min.

**Wiring point.** Already in Apollo, extend to track 1-hour /
6-hour mention velocity per market.

**Falsification.** Pick 30 resolved political markets; compute the
6-hour mention-velocity spike before each major price move; if `|ρ|` <
0.15 between velocity-z and realised |return|, signal is too noisy.

---

## 9. Options-IV term-structure (CBOE + Deribit)

**Mechanism.** For binary markets that resolve at a fixed date
(elections, earnings, central-bank meetings), implied vol from listed
options at the same expiry contains forward-looking risk premium that
Polymarket sometimes underprices. The basis between
`implied_options_vol` and `polymarket_vol_implied_by_spread` is the
edge.

**Data source.**
- [CBOE LiveVol public](https://www.cboe.com/data/historical-options-data/)
  — free historical, paid live.
- [Deribit public API](https://docs.deribit.com/) — fully open, no
  key, real-time BTC + ETH options.

**Wiring point.** Pythia: `services/pythia/src/pythia/options_iv.py`.
Apollo feature: `volatility_score` already exists — extend with an
options-IV term-structure input.

**Falsification.** For 6 months of binary Polymarket markets that
straddle a known event (FOMC, CPI), compute `options_iv - polymarket_iv`
at T-3 days. If the top decile doesn't beat the rest by > 1.5pp net of
fees, no edge.

---

## 10. Calibrated LLM ensemble disagreement (the Pantheon edge)

**Mechanism.** The most speculative entry, the one closest to what
Pantheon is built for. Run a council of N LLMs (Anthropic + Gemini +
OpenAI + DeepSeek + Llama 70B on Groq) over the same signal. The
*disagreement* itself is a feature — councils where the variance of
council_probability across providers is high carry more information
than councils where everyone agrees with the market.

**Data source.** None external — the council emits this internally.
Already plumbed in via [`services/ostrakon/src/ostrakon/diversity.py`](../services/ostrakon/)
and `services/boule/src/boule/diversity.py`.

**Wiring point.** Apollo feature: `council_diversity_score` — high
inter-provider variance + high mean-edge → up-weight; low variance + high mean-edge → flag for groupthink (Eris compensates).

**Falsification.** This is the experiment. Run 200 paper trades with
the multi-provider council enabled. Compare Brier scores to
single-provider Brier. If the multi-provider Brier improvement < 0.02
absolute, the ensemble isn't earning its compute cost.

---

## What to do with this list

If you're starting cold:

1. **Pick one source.** Wire it. Confirm the data flows end-to-end
   into Apollo via the existing `Signal` schema.
2. **Backtest with the existing harness.** `scripts/live_paper_trade_coingecko.py`
   is the template — swap `council_probability()` for a function that
   uses the source. Sweep edge thresholds.
3. **Falsify hard.** Use the criterion in this doc for the source. If
   it fails, do not double down with bigger size — pick the next one.
4. **Only after a source clears falsification** do you wire it into the
   live Apollo path. Trade it on paper for 30 days. Then `EXECUTION_MODE=live`.

The fastest path to a *bad* outcome is to chase every entry in this
list at once. Each source has nuances the next operator after you needs
to maintain. One working source > five half-wired ones.

---

## What this list deliberately does not include

- **"Insider information."** If you have it, you don't need this repo.
  If you don't, this repo doesn't help you fake it.
- **Paid alpha vendors.** Several exist; none are MIT-compatible.
- **Custom ML models trained on private data.** Worth doing, but not a
  *public* edge source — it's your edge source, not a starting point.
- **Pure technical analysis on Polymarket order books.** The book is
  too thin and reflexive for orderflow alpha at retail size; you will
  be picked off by makers.

---

## Licences

Every external API or dataset above is documented with its licence
status. Most are public / free / CC-BY. Commercial deployment should
re-verify each licence at the time of use — the data landscape moves.
The Pantheon code in `services/` is MIT; the *use* of an external data
source is governed by that source's terms.
