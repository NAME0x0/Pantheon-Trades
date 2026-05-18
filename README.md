<div align="center">

<img src="https://api.iconify.design/game-icons/greek-temple.svg?color=%23d4a85e" alt="Pantheon Trades emblem" width="120" />

# Pantheon Trades

**An AI council debates every prediction-market trade before it fires. Restraint is recorded on-chain.**

[![Foundry](https://img.shields.io/badge/Foundry-tests%20passing-success?logo=ethereum&logoColor=white)](./contracts)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](./services)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](./apps/web)
[![Chain](https://img.shields.io/badge/Arc%20Testnet-5042002-c8a85a)](https://testnet.arcscan.app)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

[Live demo](https://pantheon-trades-web.vercel.app) ·
[Architecture](./docs/ARCHITECTURE.md) ·
[Agents](./docs/AGENTS.md) ·
[Constitution](./docs/CONSTITUTION.md)

</div>

> **Hackathon judges:** the submission packet lives at [`docs/HACKATHON_SUBMISSION.md`](./docs/HACKATHON_SUBMISSION.md) — video script, Circle-tools checklist, traction template. Built for the **Agora Agents Hackathon** · Canteen × Circle × Arc · May 11–25 2026 · RFB 02 (Prediction Market Trader Intelligence). Polymarket V2 builder codes + Arc-anchored reasoning traces wired per the hackathon research notes.

---

## TL;DR (60 seconds, no jargon)

**What it is.** A trading system that doesn't trade until ten AI agents — each playing a role: bull, bear, risk officer, execution clerk — argue about the trade and vote. Two of them can refuse alone. When the system *declines* a trade, it stamps that decision onto a public blockchain so anyone can audit the discipline later.

**Why that's different.** Most trading bots are a black box optimising one number: profit. This one is glass-box, optimising two things at once — profit *and* a public record of every trade it walked away from. Walking away is half the alpha. *Showing* that you walked away is what makes it auditable.

**What you can do with it right now.**
1. Open [the live demo](https://pantheon-trades-web.vercel.app/demo). Four real captured deliberations replay event-by-event in your browser — a Bitcoin approval, a Bitcoin veto, a US-election NO trade, and an NFL market the system refused. No login. Optional wallet connect to see the on-chain side.
2. Clone this repo. The whole thing runs locally with one `docker compose up`. Use `gemini`, `openai`, `anthropic`, `openrouter`, `groq`, `together`, `deepseek`, `xai`, or a local `ollama` / `lm_studio` server — same code path, swap an env var.
3. Run a paper trade against real CoinGecko prices: `python scripts/live_paper_trade_coingecko.py`. Artifact lands in `artifacts/` with PnL, fees, drawdown, and Sharpe.

**Will it make you money?** Honest answer further down in the FAQ. Short version: the harness shows the pipeline runs end-to-end on live data, and it also shows naïve strategies lose money to fees. The hard part — finding signals where the edge survives 4% round-trip costs — is what the council exists to filter.

> **Try it now (no install):** [pantheon-trades-web.vercel.app/demo](https://pantheon-trades-web.vercel.app/demo)
>
> **Try it locally (no API key):** `pnpm install && pnpm --filter @pantheon/web dev`
>
> **Try it with your own LLM:** `BOULE_LLM_PROVIDER=openai OPENAI_API_KEY=... uv run python scripts/live_test_gemini.py`

---

## What this actually is

**For a trader:** a half-Kelly position sizer wrapped around a 10-agent deliberation that vetoes anything breaking 26 explicit risk rules. The constitution caps single-position size at 5% of NAV, single-category exposure at one of {politics 4%, crypto 5%, sports 3%, science 2%}, and a 50% gross drawdown stops opening new positions for 30 days. Half-Kelly, not full — never. Edge below 2pp after fees, never.

**For an engineer:** a Python monorepo (uv per service, no shared `pip`) of 13 deployable services behind a FastAPI gateway, a Next.js 14 marketing site, and a Foundry-built Solidity contract suite on Circle Arc Testnet. Provider-agnostic LLM layer. 334 Python tests. 51 Foundry tests + 2 symbolic specs proved by Halmos. Prometheus + Grafana provisioned. Backups hourly. Secrets in SOPS+age. Migration via Alembic async.

**For a researcher:** a council whose composition itself is the experiment. Round-1 openings, round-2 challenges, Athena's round-3 synthesis, round-4 blind votes. Two agents (Zeus, Solon) have veto power and can short-circuit the debate. One adversarial agent (Eris) reads the round-1 transcript and argues the minority side to force the council off groupthink. Agent weights update from Brier scores. Leave-one-out council ablation tells you which agents are pulling weight.

**For a sceptic:** the *no-trade* path is on-chain, not the *trade* path. So either the system declines real trades (in which case the chain is the receipt) or it doesn't (in which case the chain is empty and the claim is falsified). The first witness is at [block 42,337,549](https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb).

> **First on-chain restraint witness — recorded live during build:**
> [`0xf9ae0e7b…df960e62ba238e53a828dfa4edb`](https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb) · block `42,337,549` · `onchain_proof_id = 1`

---

## Plain-English glossary

The agents are named after Greek gods. Each name maps to one job. You only need the right column:

| Name | What it actually does |
|------|-----------------------|
| **Pythia** | Goes and gets the data (Polymarket book, news headlines, crowd sentiment, on-chain TVL, Kalshi). |
| **Apollo** | Builds a scored signal from Pythia's data and rates it S/A/B/C/D. |
| **Boule** | Runs the deliberation — the round-1..round-4 council. The orchestrator. |
| **Ares, Hades** | Bull researchers. Argue *for* the trade. |
| **Athena, Cassandra** | Bear researchers. Argue *against*. Athena also writes the round-3 synthesis. |
| **Zeus** | Risk officer. Can veto alone on constitutional violations. |
| **Solon** | Compliance officer. Can veto alone on regulatory / liquidity / category-cap violations. |
| **Themis** | Procedural arbiter. Checks for data freshness, source integrity, recommends resizes. |
| **Hephaestus, Daedalus** | Execution planners. Pick maker vs taker, model slippage, design exits. |
| **Humans** | Crowd-sentiment input — Reddit, Twitter (via Nitter), trade-news. |
| **Eris** | Adversarial dissenter. Reads round-1, argues the minority side hard. Opt-in. |
| **Areopagus** | The court. Final gatekeeper. Half-Kelly sizer. Writes Proof of Restraint on rejection. |
| **Strategos** | The exchange clerk. Routes the trade to Polymarket CLOB (paper or live). |
| **Argos** | Watches open positions. Surfaces stuck payouts, exits via Argos rules. |
| **Parthenon** | Archive. IPFS + Irys bundles every deliberation. ERC-8004 agent passports. |
| **Ostrakon** | Scoring. Brier scores, Sharpe, calibration, agent leaderboards. |
| **Underworld** | Post-mortems. Reflects on losing trades, proposes prompt edits. |
| **Olympus** | Coordinator. Goals board. Adversarial-mode trigger. |
| **Moirai** | Strategy lifecycle (Clotho, Lachesis, Atropos — spin, allocate, retire). |
| **Elysium** | Backtest + paper arena. |

If a name confuses you in any document, look here first.

---

## What's distinctive

| | |
|---|---|
| **Ten agents, four rounds** | Bull pair (Ares, Hades), bear pair (Athena, Cassandra), risk triad (Zeus, Solon, Themis), execution triad (Hephaestus, Daedalus, Humans). Openings → challenges → Athena synthesis → blind votes. |
| **Two veto powers** | Zeus and Solon can halt a trade unilaterally on a constitutional violation. Early-veto short-circuits the debate to save tokens. |
| **Half-Kelly with caps** | Areopagus sizes positions using directional edge and a confidence-weighted half-Kelly fraction, then clamps against constitutional position limits and category exposure. |
| **Proof of Restraint** | When the council declines, Areopagus writes a `Restrained(signalHash, marketId, reasonCode, note)` record to a deployed Solidity contract on Arc. The repo's flagship feature is provably live at [`0x4b35…4895`](https://testnet.arcscan.app/address/0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895). |
| **Pluggable LLMs (11 providers)** | One env var switches Anthropic / Gemini / OpenAI / OpenRouter / Groq / Together / DeepSeek / xAI Grok / Fireworks / local Ollama / local LM Studio / any self-hosted OpenAI-compatible server. See [LLM provider matrix](#llm-provider-matrix). |
| **Portable identities** | ERC-8004 agent passports — councilors carry their reputation across deployments. |
| **Self-calibrating** | Agent weights update from realised Brier scores. Platt + isotonic regression recalibrate council probability from outcomes. Slippage learner refines from each fill. The system gets sharper the longer it runs. |

---

## LLM provider matrix

The council debate code is written against one `LLMClient` protocol so the provider is a config switch, not a code path. Pick whichever LLM you have a key for (or run locally on Ollama / LM Studio):

| Provider | `BOULE_LLM_PROVIDER` | Required env | Notes |
|----------|----------------------|--------------|-------|
| **Anthropic Claude** | `anthropic` *(default)* | `ANTHROPIC_API_KEY` | Best reasoning depth for the council role-plays; what most production tests are pinned to. |
| **Google Gemini** | `gemini` | `GEMINI_API_KEY` | Free tier supports 25k RPD on flash-lite. `scripts/live_test_gemini.py` targets this directly. |
| **OpenAI** | `openai` | `OPENAI_API_KEY` (+ `OPENAI_MODEL`) | Standard OpenAI `/v1/chat/completions`. Default model `gpt-4o-mini`. |
| **OpenRouter** | `openrouter` | `OPENROUTER_API_KEY` (or `OPENAI_API_KEY`) | One key → 200+ models. Pin a specific model with `OPENROUTER_MODEL=anthropic/claude-sonnet-4`. |
| **Groq** | `groq` | `GROQ_API_KEY` | Fastest inference on the list. Default `llama-3.1-70b-versatile`. |
| **Together AI** | `together` | `TOGETHER_API_KEY` | Open-weight models. Default `meta-llama/Llama-3.3-70B-Instruct-Turbo`. |
| **DeepSeek** | `deepseek` | `DEEPSEEK_API_KEY` | Cheap; `deepseek-chat` / `deepseek-reasoner`. |
| **xAI Grok** | `xai` (or `grok`) | `XAI_API_KEY` | `grok-2-latest` by default. |
| **Fireworks / vLLM / TGI / LocalAI** | `openai_compat` | `OPENAI_BASE_URL` + `OPENAI_API_KEY` + `OPENAI_MODEL` | Generic OpenAI-compatible server escape hatch. |
| **Ollama (local)** | `ollama` | none (auto-detects `http://localhost:11434/v1`) | Default model `llama3.1`. Override with `OLLAMA_MODEL`. |
| **LM Studio (local)** | `lm_studio` | none (auto-detects `http://localhost:1234/v1`) | Default model `local-model`. Override with `LM_STUDIO_MODEL`. |

Every provider shares the same cache, retry-with-backoff, semaphore concurrency limit, and minimum-spacing throttle. If you've taken any LLM call before, you know how this one works — except it also caches identical-input → identical-output for free re-runs in your CI.

```bash
# Run the same script against four providers without touching any code:
BOULE_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=...   uv run python scripts/live_test_gemini.py
BOULE_LLM_PROVIDER=openai    OPENAI_API_KEY=sk-...   OPENAI_MODEL=gpt-4o-mini   uv run python scripts/live_test_gemini.py
BOULE_LLM_PROVIDER=groq      GROQ_API_KEY=gsk-...    GROQ_MODEL=llama-3.1-70b-versatile   uv run python scripts/live_test_gemini.py
BOULE_LLM_PROVIDER=ollama    OLLAMA_MODEL=llama3.1   uv run python scripts/live_test_gemini.py
```

Source: [`services/boule/src/boule/llm/__init__.py`](./services/boule/src/boule/llm/__init__.py).

---

## Recent additions (Tier A–G build)

A seven-tier robustness pass landed in 35 commits. Highlights below; full per-feature notes in [docs/CHANGELOG_TIERS.md](./docs/CHANGELOG_TIERS.md).

| Tier | What shipped |
|------|--------------|
| **A — survival foundation** | Prometheus metrics + Grafana dashboard · Polymarket L2 WebSocket depth · correlation-aware portfolio sizing · multi-sig admin migration script for ProofOfRestraint · Hypothesis property tests across sizing / calibration / slippage. |
| **B — execution quality** | Drawdown-adjusted Kelly · walk-forward / decayed calibration windows · Argos resolution-lag state machine · Strategos maker/taker chooser · online slippage learner that refines from realised fills. |
| **C — intelligence** | Pluggable RAG (in-memory cosine + optional ChromaDB) over resolved markets · Eris adversarial dissenter against council groupthink · reflection-driven prompt evolution from Underworld post-mortems · agent ablation via leave-one-out council Brier · Nitter RSS X/Twitter sentiment with built-in VADER-style scorer. |
| **D — venues + data** | Kalshi venue connector · DeFiLlama TVL + stablecoin flows + yields · TradingView screener adapter · spaCy/regex news-headline NER and market matcher. |
| **E — operational maturity** | Alembic async migrations · hourly Postgres + Redis backup compose service · Mozilla SOPS + age secrets · slowapi global rate limiting · `/health/deep` probes (Redis info / DB version / RPC chainId / IPFS id). |
| **F — frontend** | Pure-SVG trace Sankey · line + bar chart primitives + perf metrics (equity, rolling Sharpe, max DD) · manual trade-approval card · Brier-ranked agent leaderboard. |
| **G — safety hygiene** | mutmut mutation testing scaffold · Shopify Toxiproxy chaos drills · a16z Halmos symbolic specs for ProofOfRestraint + PantheonConstitution · IRS Form 8949 tax CSV export. |

Every upstream picked is open-source MIT/Apache and runs without paid vendors: ChromaDB, Nitter, Kalshi REST, DeFiLlama public API, tradingview-screener, spaCy, Alembic, SOPS + age, slowapi, mutmut, Toxiproxy, Halmos.

---

## Empirical adoption verdicts (live backtest)

Ran `scripts/backtest_sources_xml.py` against 200 resolved Manifold binary markets in council mode (5 distinct roles aggregated per market). Headline numbers from the most recent runs:

| Forecaster | Brier ↓ | Reliability ↓ | Resolution ↑ |
|------------|---------|---------------|--------------|
| Manifold consensus | **0.126** | 0.012 | 0.123 |
| Single-shot Gemini | 0.260 | 0.046 | 0.049 |
| **5-role council (API)** | **0.149** | 0.019 | 0.088 |

**Council aggregation closes 80% of the Gemini-vs-Manifold Brier gap.** Calibration is close to Manifold; the remaining gap is *resolution* — the council blurs outcomes into less-distinguishable bins than play-money humans do.

Per-source adoption at council baseline (200-market sample): **zero ADOPT** — all 12 sources HOLD or untestable. At sharper aggregator output, individual source contributions compress to noise. The aggregation itself is the bigger win than any single source signal.

Adoption verdicts at the *single-shot* baseline (less sharp aggregator, more room for sources to help):

| Source | Δ Brier vs single-shot baseline | Applicability | Verdict |
|--------|---------------------------------|---------------|---------|
| **attention** (Wikipedia pageviews) | −0.0040 | 33.5% | **ADOPT** |
| **crowd_sentiment** (Nitter) | −0.0040 | 36.0% | **ADOPT** |
| 7 others (orderbook_imbalance, perps, geo, onchain_tvl, lead_lag, etc.) | ±0.0001–0.0010 | 5–14% | HOLD |
| 3 untestable on Manifold-only data | — | — | basis_arb, consensus_delta, macro_basis |

Full per-source decomposition + ranked next-step actions in [`docs/BACKTEST_RESULTS.md`](./docs/BACKTEST_RESULTS.md). The biggest profit-relevant takeaways:

1. **The council aggregation is the moat** — switching from single-shot to 5-role aggregated halves the Brier delta to Manifold.
2. **Manifold consensus is a stiff benchmark** — beating it on random questions is the empirical bar for "the council adds informational value beyond free human consensus."
3. **Sources help most at single-shot baseline; less at council baseline** — implies the operator either trusts the council aggregate alone OR routes harder questions (where council is noisier) through the source-augmented path.
4. **Wikipedia + Nitter** are the two operational ADOPT signals. Both already wired in `apollo.scorer` at ±0.05 caps — no code change needed.

Latest 200-market run cost: **$0.025** on Gemini flash-lite. Refreshable weekly.

---

## Profitability-readiness build (post Tier A–G)

After Tier A–G the project had hardened plumbing but no proven *edge source*. Six waves landed since to close that gap. The honest bottom line is in [`docs/FEES_AND_EDGE.md`](./docs/FEES_AND_EDGE.md) — short version below.

| Wave | What shipped | Why it matters |
|------|--------------|----------------|
| **1 — fee path** | `post_only` flag plumbed `OrderRequest → LiveExecutor → choose_execution`; new `strategos.maker_rebate.FeeLedger` accounts per-trade fees + rebates per the Polymarket V2 schedule. | Switches a patient politics trade from –4% round-trip to **+88 bps** rebate inflow. Validated: 4 maker trades on the synthetic Polymarket harness accrued $21.41 in rebates against $0 fees — same trades all-taker would have cost ~$76. |
| **2 — 3 new pythia sources** | `wikipedia.py` (pageviews + attention z-score), `fred.py` (816k macro time series, no key required), `manifold.py` (free human consensus prior). All async, all hermetically tested. | Plumbs the *unconsidered* public-data feeds catalogued in [docs/EDGE_SOURCES.md](./docs/EDGE_SOURCES.md). Each one validated against a falsification criterion before it earns a spot in the live signal. |
| **3 — 4 new Apollo features** | `geopolitical_risk` (GDELT volume + tone composite), `attention` (Wikipedia velocity sigmoid), `macro_basis` (FRED gap with tanh saturation), `consensus_delta` (Manifold ≠ Polymarket → sizing cap). Each capped at ±0.05 oracle-probability movement so no single source dominates. | Turns raw pythia signals into bounded oracle-probability adjustments. Combined cap of ±0.20 leaves the council with real say. |
| **4 — Apollo scorer wiring** | `score_market` now consumes the four new features as optional `MarketSnapshot` fields. Legacy callers unchanged. | The new sources actually reach `Signal.oracle_probability` end-to-end. 11 integration tests verify each delta moves the right direction by the right amount, and unused features stay no-ops. |
| **5 — Conformal prediction** | `ostrakon.conformal_calibration` — split + adaptive (time-decayed) variants. `ConformalInterval` around any council probability. `conservative_kelly_p()` returns the lower bound. | Distribution-free, finite-sample coverage guarantees on probability intervals. Areopagus can size against `p_lo` instead of the point estimate — natural Kelly overconfidence regulariser at the [0, 1] extremes. |
| **6 — Falsification + Polymarket paper** | `scripts/backtest_council_vs_manifold.py` (offline / heuristic / **full** modes — full hits real Anthropic / Gemini / OpenAI / Groq / etc); `scripts/paper_trade_polymarket.py` runs the whole pipeline against the live Polymarket book with proper fee accounting (synthetic fallback when Polymarket geo-blocks). | The empirical falsification question — *does Boule beat free Manifold consensus on N resolved markets?* — is now one shell command. The Polymarket harness is the 30-day precondition before `EXECUTION_MODE=live`. |

```bash
# Cheap sanity (no LLM calls — runs against 50 resolved Manifold markets)
python scripts/backtest_council_vs_manifold.py --mode=offline --n=50

# Real council via Gemini, 100 markets, ≈ $0.02 total
BOULE_LLM_PROVIDER=gemini GEMINI_API_KEY=AIza... \
  python scripts/backtest_council_vs_manifold.py --mode=full --n=100

# 30-day paper test against live Polymarket flow
python scripts/paper_trade_polymarket.py --markets=50 --edge-threshold=0.04
```

**What this does NOT do:** find a working edge source for you. The pipeline is now profit-capable — `Signal → Thesis → Approval → Maker Rebate` is end-to-end with the new feature sources and proper fee accounting. The remaining work is empirical: pick one source from [`docs/EDGE_SOURCES.md`](./docs/EDGE_SOURCES.md), validate it on resolved markets through the council-vs-Manifold harness, and only ship to live mode once the Brier delta is negative on a 200+ market sample.

---

## How it works

```mermaid
%%{init: {'theme':'base','themeVariables':{
  'primaryColor':'#0a0e16','primaryTextColor':'#f7f3e9','primaryBorderColor':'#c8a85a',
  'lineColor':'#c8a85a','secondaryColor':'#1a1f2e','tertiaryColor':'#0a0e16',
  'fontFamily':'Georgia, serif'}}}%%
flowchart TD
    Pythia([<b>Pythia</b><br/><i>oracle</i><br/>Polymarket · news · prices])
    Apollo([<b>Apollo</b><br/><i>signals</i><br/>7-dim scoring · A/B/C bands])
    Boule([<b>Boule</b><br/><i>council</i><br/>10 agents · 4 rounds])
    Areopagus{{<b>Areopagus</b><br/><i>court</i><br/>gates · half-Kelly}}
    Strategos([<b>Strategos</b><br/><i>execution</i><br/>CLOB router])
    Parthenon[(<b>Parthenon</b><br/><i>archive</i><br/>IPFS · Irys · Merkle)]
    ProofRestraint[/<b>ProofOfRestraint</b><br/>on-chain witness/]
    Argos([<b>Argos</b><br/><i>monitor</i><br/>exits])
    Ostrakon([<b>Ostrakon</b><br/><i>scoring</i><br/>Brier · Sharpe])
    Underworld([<b>Underworld</b><br/><i>post-mortem</i>])
    Olympus([<b>Olympus</b><br/><i>coordinator</i><br/>goals · adversarial])

    Pythia -- raw signal --> Apollo
    Apollo -- Signal --> Boule
    Boule -- Thesis + traces --> Areopagus
    Areopagus -- ApprovalToken --> Strategos
    Areopagus -- RejectionRecord --> ProofRestraint
    ProofRestraint -. anchored on .-> ArcChain[(<b>Arc Testnet</b><br/>chain 5042002)]
    Strategos -- Trade --> Argos
    Argos -- Outcome --> Ostrakon
    Strategos --> Parthenon
    Boule --> Parthenon
    Ostrakon --> Underworld
    Ostrakon --> Olympus
    Underworld --> Olympus

    classDef gold fill:#0a0e16,stroke:#c8a85a,stroke-width:1.5px,color:#f7f3e9
    classDef court fill:#1a1f2e,stroke:#c8a85a,stroke-width:2px,color:#c8a85a
    classDef chain fill:#0a0e16,stroke:#c8a85a,stroke-width:1.5px,color:#c8a85a,stroke-dasharray:4 3
    class Pythia,Apollo,Boule,Strategos,Argos,Ostrakon,Underworld,Olympus,Parthenon gold
    class Areopagus court
    class ProofRestraint,ArcChain chain
```

Every box emits structured `TraceEvent`s to Redis. The `/demo` route in the web app replays a captured deliberation event-by-event so you can watch a council form an opinion in real time.

---

## The council

```mermaid
%%{init: {'theme':'base','themeVariables':{
  'primaryColor':'#0a0e16','primaryTextColor':'#f7f3e9','primaryBorderColor':'#c8a85a',
  'lineColor':'#c8a85a','clusterBkg':'#0a0e16','clusterBorder':'#c8a85a',
  'fontFamily':'Georgia, serif'}}}%%
flowchart LR
    subgraph BULL [<b>Bull</b>]
        Ares([Ares])
        Hades([Hades])
    end
    subgraph BEAR [<b>Bear</b>]
        Athena([Athena ✦])
        Cassandra([Cassandra])
    end
    subgraph RISK [<b>Risk</b>]
        Zeus([Zeus ⚡])
        Solon([Solon ⚡])
        Themis([Themis])
    end
    subgraph EXEC [<b>Execution</b>]
        Hephaestus([Hephaestus])
        Daedalus([Daedalus])
        Humans([Humans])
    end

    BULL --- BEAR --- RISK --- EXEC

    classDef agent fill:#0a0e16,stroke:#c8a85a,stroke-width:1px,color:#f7f3e9
    classDef veto fill:#1a1f2e,stroke:#c8a85a,stroke-width:2px,color:#c8a85a
    class Ares,Hades,Cassandra,Hephaestus,Daedalus,Humans,Themis agent
    class Athena,Zeus,Solon veto
```

> ⚡ veto power · ✦ also writes the round-3 synthesis

Twelve additional agents orchestrate (Apollo, Boule, Areopagus, Strategos, Argos, Ostrakon, Parthenon, Pythia, Elysium, Underworld, Moirai, Olympus) — full roster in [docs/AGENTS.md](./docs/AGENTS.md).

---

## Quick start

**Local dev — full stack:**

```bash
# clone, install, copy env
git clone https://github.com/NAME0x0/Pantheon-Trades
cd Pantheon-Trades
pnpm install
cp .env.example .env       # then fill in keys (see below)

# bring up Postgres + Redis + IPFS + every service
docker compose up -d

# run gates
pnpm test                  # node + python suites
forge test --root contracts # 51 tests across 18 suites
python tests/bench.py      # full microbenchmark + bench harness
```

**Just the demo site:**

```bash
pnpm --filter @pantheon/web dev
# open http://localhost:3000
```

**Fire one real restraint witness on Arc Testnet:**

```bash
uv run python tests/dry_run_chain_write.py
# → Arcscan link printed at end
```

**Required env keys** (full list in [`.env.example`](./.env.example)):

| Key | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` *or* `GEMINI_API_KEY` | Council deliberation |
| `RPC_URL`, `PRIVATE_KEY`, `CHAIN_ID` | Arc Testnet writes |
| `PROOF_OF_RESTRAINT_ADDRESS` | Enables on-chain restraint anchoring |
| `DATABASE_URL`, `REDIS_URL` | Service backbone |
| `POLYMARKET_API_KEY/SECRET/PASSPHRASE` | Live CLOB execution (optional) |

---

## Verification gates

This repo treats correctness as a deploy gate, not a hope. The current `main` passes:

```
forge test               20 suites · 51 tests + 2 symbolic specs · 0 failed
halmos                   ProofOfRestraint + PantheonConstitution invariants proved
python -m compileall     340+ files · 0 syntax errors
pytest sweep             520+ tests across 12 service suites
docker compose config    valid (incl. observability + backup stack)
pnpm install             clean (node-linker=hoisted)
pnpm --filter web build  56 routes · /demo first-load 126 kB
tests/bench.py           every microbenchmark gate green
ruff check               all checks passed
```

Run them yourself before touching anything: `python tests/bench.py`.

---

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | Next.js 14 App Router + shadcn/ui + Tailwind | Server components, streaming, accessible primitives |
| API gateway | FastAPI (Python 3.12, uv) | Async, typed, plays well with the rest of the Python stack |
| Services | Python 3.12, one `uv` env per service | Independent deploys, no shared `pip` blast radius |
| LLM | Anthropic Claude or Google Gemini (pluggable via `LLMClient` protocol) | Provider redundancy, per-call retry/timeout/throttle in isolated modules |
| Contracts | Solidity 0.8.24, Foundry, OpenZeppelin AccessControl + MerkleProof | Audited primitives, fast tests, predictable gas |
| Chain | Circle Arc Testnet — chain id `5042002`, native USDC gas | Built for stablecoin-denominated financial primitives |
| Prediction market | Polymarket CLOB | Deepest liquidity for binary outcome markets |
| Storage | PostgreSQL · Redis Streams · IPFS · Irys | Operational state, pub/sub, content-addressed archive, permanent bundle |
| Monorepo | pnpm workspaces + Turborepo + uv | Single lockfile, cached builds, no node↔python coupling |

---

## Repo layout

```
apps/
  web/          Next.js 14 marketing site + replay viewer + dashboard
  api/          FastAPI gateway · SIWE auth · Redis-backed routes

services/
  apollo/       Signal generation + 7-dimension band scoring
  areopagus/    Risk gating · half-Kelly · on-chain restraint writer
  argos/        Position monitoring + exit signals
  boule/        Multi-agent council orchestrator + LLM adapters
  elysium/      Backtesting + paper arena
  moirai/       Strategy lifecycle (Clotho · Lachesis · Atropos)
  olympus/      System governance · goals board · adversarial mode
  ostrakon/     Agent scoring · Brier · calibration · Sharpe
  parthenon/    IPFS · Irys · Merkle archival · ERC-8004 passports
  pythia/       Data oracle · Polymarket · news · sentiment
  strategos/    CLOB router · paper and live execution
  underworld/   Post-mortems + counterfactual analysis

packages/
  pantheon-core/  Shared Pydantic schemas + utilities

contracts/      Foundry — Arc Testnet smart contracts
  src/          ProofOfRestraint · ThesisRegistry · SignalRegistry ·
                PantheonConstitution · DecisionCourt · NoTradeAlpha ·
                AgentReputation · ExecutionVault · …
  test/         51 tests across 18 suites

db/             SQL schema (9 tables)
docs/           Full design documentation
infra/          Compose, Dockerfiles, deploy scripts
tests/          Cross-service benchmarks + live dry-runs
```

---

## Documentation

| Doc | What's inside |
|-----|---------------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | End-to-end system design |
| [AGENTS.md](./docs/AGENTS.md) | All 22 agents, weights, veto authority |
| [CONSTITUTION.md](./docs/CONSTITUTION.md) | Immutable system rules — quorum, vetoes, position caps |
| [SIGNAL_SPEC.md](./docs/SIGNAL_SPEC.md) | Signal envelope schema and scoring dimensions |
| [THESIS_SCHEMA.md](./docs/THESIS_SCHEMA.md) | Thesis structure produced by Boule |
| [RISK_POLICY.md](./docs/RISK_POLICY.md) | Position limits, drawdown gates, category exposure |
| [TRACE_FORMAT.md](./docs/TRACE_FORMAT.md) | `TraceEvent` schema emitted on every agent step |
| [SETTLEMENT_FLOW.md](./docs/SETTLEMENT_FLOW.md) | On-chain settlement and archival path |
| [MOIRAI_LAWS.md](./docs/MOIRAI_LAWS.md) | Strategy lifecycle: creation, assignment, termination |

---

## Status

**Working today**

- Full Boule council against live Gemini (default `gemini-2.5-flash-lite`, ~6s spacing on free tier) and Anthropic providers · Eris adversarial dissenter opt-in via `BOULE_ERIS_ENABLED=1`
- Areopagus gating · half-Kelly · drawdown haircut · correlation-aware sizing · constitutional caps
- Strategos paper book execution + maker/taker chooser + online slippage learner
- Pythia connectors: Polymarket REST + L2 WebSocket · Kalshi · DeFiLlama · TradingView screener
- Apollo features: RAG over resolved markets · Nitter crowd sentiment · news-NER market matcher · on-chain TVL
- Argos resolution-lag state machine surfacing stuck-payout positions
- Observability: Prometheus metrics on every council service · provisioned Grafana dashboard at :3001
- Backup: hourly pg_dump + Redis BGSAVE · retention configurable · operator runbook in `infra/backup`
- Secrets: SOPS + age for encrypted `.env.enc` and `infra/secrets/*.yaml`
- Static demo site on Vercel with interactive council replay + Sankey trace · approval card · leaderboard primitives
- **Proof of Restraint anchored on Arc Testnet — first witness in [block 42,337,549](https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb)** · multi-sig migration script ready in `contracts/script/TransferRestraintAdmin.s.sol`
- Symbolic verification (Halmos) on `ProofOfRestraint` and `PantheonConstitution` runs in CI alongside Foundry tests
- 53+ Foundry suites · 334+ Python tests · full compose stack healthy

**On the roadmap**

- Live Polymarket CLOB routing (paper mode complete, live mode behind `EXECUTION_MODE=live`)
- Parthenon Merkle batching + Arc anchor cadence tuning
- ERC-8004 passport portability across testnets
- Adversarial-mode strategy retirement via Moirai (council adversarial agent shipped; lifecycle retirement next)

---

## Live tests + artifacts

Two harnesses you can run today to see the system move under your own keys / against real data:

### 1. Gemini live council deliberation

```bash
uv run --project services/boule --with httpx python scripts/live_test_gemini.py
# -> artifacts/live_test_<UTC>.json
```

Walks ten agents through round 1 (opening) and round 4 (vote) against `gemini-2.5-flash-lite` (overridable via `BOULE_GEMINI_MODEL`). Records per-call duration, token in/out, finish reason, model fingerprint, and an estimated USD cost. Spacing defaults to 6.2s for free-tier compliance — bump down via `LIVE_TEST_SPACING_S=0.5` on paid tier (25k RPD).

The canonical artifact is checked in at [`artifacts/live_test_20260517T034219Z.json`](./artifacts/live_test_20260517T034219Z.json) — 20/20 successful calls, 364 seconds, **$0.00266 estimated cost**. See [artifacts/README.md](./artifacts/README.md) for full schema.

### 2. CoinGecko paper trade against live BTC prices

```bash
LIVE_PAPER_MODE=history LIVE_PAPER_DAYS=7 LIVE_PAPER_TICKS=100 \
LIVE_PAPER_EDGE_THRESHOLD=0.02 \
python scripts/live_paper_trade_coingecko.py
# -> artifacts/coingecko_paper_<UTC>.json
```

Pulls a real BTC/USD bar series from CoinGecko's free `/coins/{id}/market_chart` endpoint, builds a synthetic "will next bar print higher?" binary question per bar, sizes with the production `areopagus.kelly.size_position` (half-Kelly, 5% cap, 0.5% floor), fills through the production `strategos.paper.PaperBook` (half-spread + slippage + 2% taker fees), and settles on the next bar.

**Canonical run:** 7-day window, 100 hourly bars, 79 trades fired, **49.4% win rate**, **-39.5% PnL**, **$1,346 in fees on $10k starting bankroll**. The plumbing works end-to-end; naïve momentum doesn't survive round-trip costs. *This is by design* — the harness uses a toy momentum estimator in place of the LLM council so the result is honest, not flattering. Replace `council_probability()` with a real Boule deliberation if you want the real comparison (and the LLM bill that goes with it).

See the full breakdown at [`artifacts/coingecko_paper_20260517T091551Z.json`](./artifacts/coingecko_paper_20260517T091551Z.json).

---

## FAQ — the honest answers

Three things people ask first. Plain answers, with code pointers:

### Is this recursive? Does it self-improve?

Yes. Four feedback loops, all running today:

1. **Prompt evolution** ([`services/underworld/src/underworld/prompt_evolver.py`](./services/underworld/src/underworld/prompt_evolver.py)). Underworld writes post-mortems on settled trades. After enough samples (default 20), it proposes edits to the agent prompts in `services/boule/src/boule/prompts/`. Edits land between `LESSONS_LEARNED_START` / `LESSONS_LEARNED_END` markers so prompts stay diff-friendly.
2. **Agent weight updates** ([`services/ostrakon/src/ostrakon/agent_calibration.py`](./services/ostrakon/src/ostrakon/agent_calibration.py)). Brier scores on each agent's vote probability vs realised outcome update the agent's voting weight. Better-calibrated agents matter more next time.
3. **Walk-forward council calibration**. Platt scaling + isotonic regression are refit on a rolling window of settled trades. Optional exponential time-decay so older trades count less.
4. **Online slippage learner** ([`services/strategos/src/strategos/slippage_learner.py`](./services/strategos/src/strategos/slippage_learner.py)). EWMA per `(market, log10(depth))` bucket. Every fill that beats or misses expected price refines the next sizing call.

There's also leave-one-out council ablation (`ostrakon ablate`) that tells you which agents are pulling weight. Run it weekly. Drop the ones that aren't.

### Does it calibrate itself, or do I have to tune it?

It does, but you should *check* not *trust*. The system is shipped pre-tuned with:

- Conservative half-Kelly (not full).
- A `MAX_POSITION_PCT=5%` constitutional cap. You can lower it. You cannot raise it.
- Category exposure caps: politics 4%, crypto 5%, sports 3%, science 2%.
- A liquidity floor: $50k 24h volume. Below this, Solon rejects automatically.
- A drawdown haircut: half-Kelly multiplier ramps linearly from 1.0 → 0.2 between 0 and 30% drawdown.

You should still run the [verification gates](#verification-gates) and the CoinGecko paper harness before pointing at real capital. The calibration loops adapt the *probabilities*; they do not adapt the *risk policy*. That is yours to set.

### Will it make money if I deploy it for real, right now?

Probably not without work. Honest reasons:

- **Polymarket taker fees are 2% per side** = 4% round-trip. Any binary edge below ~6pp gets eaten by fees alone. Most binary markets do not have a 6pp edge.
- **The CoinGecko paper-trade artifact above shows -39.5% PnL on a naïve momentum strategy.** That is what happens when you fire on every tick without an edge that survives fees.
- **The council is good at refusing trades**, which is what the on-chain restraint witnesses prove. The harder, unsolved problem is *generating* signals where the edge survives fees. Apollo's seven-dimension scorer is a starting point, not a finished alpha source.
- **Live mode is gated behind `EXECUTION_MODE=live`** specifically so an enthusiastic user can't deploy paper-tested code with real money on accident.

What it is genuinely useful for *today*:

- **Auditable discipline.** If you're a fund that wants to publish proof-of-restraint as part of an investor letter, the on-chain receipts are a credible primitive.
- **Multi-agent research infrastructure.** Council composition, agent weights, and prompt evolution are all running and instrumented. Easier to experiment with here than to build from scratch.
- **A teaching tool for risk discipline.** The 26 explicit constitutional rules + the half-Kelly + drawdown haircut + category caps are conservative by design, and they're encoded in code, not posters on the wall.

What it would take to make money on real Polymarket flow:

1. A Pythia data source that genuinely sees edge other people don't (the public-data sources here are a baseline, not an alpha source).
2. Calibrated council probabilities sharper than the market on the markets you actually trade.
3. Discipline to *not* trade when the edge isn't there. (This part the system already does well.)

If you build #1 and #2, this repo handles #3 cleanly and writes the receipts to chain.

---

## Walkthrough — running it end-to-end for the first time

This works on macOS, Linux, and Windows (PowerShell). Roughly 10 minutes for a clean machine.

### 1. Prerequisites (one-time)

```bash
# Node 20+ (for the web app and the monorepo)
node --version

# pnpm (the JS package manager — fast, monorepo-friendly)
npm install -g pnpm

# uv (the Python package manager — replaces pip + venv)
curl -LsSf https://astral.sh/uv/install.sh | sh    # Linux/Mac
# Windows: irm https://astral.sh/uv/install.ps1 | iex

# Foundry (for the Solidity contracts)
curl -L https://foundry.paradigm.xyz | bash && foundryup

# Docker (for the local services stack)
# Install Docker Desktop from docker.com if you don't have it
```

If you only want to look at the demo site you can skip Foundry and Docker.

### 2. Clone + install

```bash
git clone https://github.com/NAME0x0/Pantheon-Trades
cd Pantheon-Trades
pnpm install           # installs JS deps for all packages
cp .env.example .env   # then fill in keys — see below for the minimum
```

The very minimum to *run something* is one LLM key. Either:

```env
# .env
ANTHROPIC_API_KEY=sk-ant-...    # default provider
# or
BOULE_LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
# or
BOULE_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

For everything else (chain writes, live Polymarket, IPFS archives) you'll need the keys in [`.env.example`](./.env.example). For local-only experimentation, the [LLM provider matrix](#llm-provider-matrix) lets you point at `ollama` / `lm_studio` instead and skip all paid keys.

### 3. Pick your path

**(a) Just look at the demo.** No backend, no docker, no API keys.

```bash
pnpm --filter @pantheon/web dev
# open http://localhost:3000
```

Watch four real captured deliberations replay event-by-event. Optionally connect your wallet to see the SIWE + Arc Testnet switch flow.

**(b) Run a live LLM council deliberation against your key.**

```bash
uv run --project services/boule --with httpx python scripts/live_test_gemini.py
```

Produces `artifacts/live_test_*.json` with per-agent timings and costs.

**(c) Run a paper trade against real BTC prices.**

```bash
LIVE_PAPER_MODE=history LIVE_PAPER_DAYS=7 LIVE_PAPER_TICKS=100 \
  python scripts/live_paper_trade_coingecko.py
```

Produces `artifacts/coingecko_paper_*.json` with PnL, fees, drawdown.

**(d) Bring up the whole stack.**

```bash
docker compose up -d
pnpm test
forge test --root contracts
```

13 services + Postgres + Redis + IPFS + Prometheus + Grafana. Grafana is at `http://localhost:3001` (admin / pantheon).

**(e) Fire one real Proof of Restraint on Arc Testnet.**

Needs `PRIVATE_KEY`, `RPC_URL`, `PROOF_OF_RESTRAINT_ADDRESS` in `.env`. The contract is deployed at [`0x4b35…4895`](https://testnet.arcscan.app/address/0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895). USDC is the native gas token on Arc, so you'll need test USDC in your wallet.

```bash
uv run python tests/dry_run_chain_write.py
# Arcscan link printed at end
```

---

## Polymarket integration + geo-block proxy

Polymarket geo-blocks several jurisdictions at the HTTP layer (DNS resolves, TCP handshake refused). Pantheon ships a Vercel-Edge proxy at [`apps/web/app/api/polymarket-proxy/[...path]/route.ts`](./apps/web/app/api/polymarket-proxy/[...path]/route.ts):

```
/api/polymarket-proxy/gamma/...   →  https://gamma-api.polymarket.com/...
/api/polymarket-proxy/clob/...    →  https://clob.polymarket.com/...
/api/polymarket-proxy/data/...    →  https://data-api.polymarket.com/...
```

After deploying `apps/web` to Vercel, point Pantheon services at the proxy:

```env
POLYMARKET_CLOB=https://<your-vercel-app>.vercel.app/api/polymarket-proxy/clob
POLYMARKET_GAMMA=https://<your-vercel-app>.vercel.app/api/polymarket-proxy/gamma
POLYMARKET_PROXY_TOKEN=<a long random string — optional shared secret>
```

All four Polymarket-touching call sites (`services/pythia/src/pythia/polymarket.py`, `services/strategos/src/strategos/polymarket_clob.py`, `services/strategos/src/strategos/consumer.py`, `scripts/paper_trade_polymarket.py`) read these env vars and fall back to the direct hosts when unset.

Full Polymarket integration checklist (creds, builder code, wallet funding, security): [`docs/POLYMARKET_INTEGRATION.md`](./docs/POLYMARKET_INTEGRATION.md).

---

## License

MIT — see [LICENSE](./LICENSE).
