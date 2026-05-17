# Tier A–G Changelog

Comprehensive per-feature notes for the 35-commit robustness pass. Each
section lists the user-visible behaviour, the modules added, the tests
covering them, and the open-source licence of any new third-party
upstream.

---

## Tier A — Survival foundation

### A.1 · Hypothesis property tests
**Commit:** `5a4da79`
**Modules:** `services/areopagus/tests/test_property_kelly.py`,
`services/strategos/tests/test_property_slippage.py`,
`services/boule/tests/test_property_calibrator.py`
**Adds:** 20 invariant tests across Kelly sizing, slippage curves, and
calibration with the Hypothesis property-based engine.
**Upstream:** Hypothesis (MPL-2.0).

### A.2 · Polymarket L2 WebSocket depth
**Commit:** `9a15491`
**Module:** `services/pythia/src/pythia/polymarket_ws.py`
**Adds:** Async `PolymarketL2Client` with exponential reconnect,
`inject_for_testing()` seam, depth-level parsing.

### A.3 · Correlation-aware sizing
**Commit:** `94c0741`
**Module:** `services/areopagus/src/areopagus/correlation_sizing.py`
**Adds:** `correlation_aware_size(...)` shrinks proposed size by
`max(min_mult, 1 − |max_corr|)`. Prevents two correlated longs from
doubling hidden exposure.

### A.4 · ProofOfRestraint multi-sig admin migration
**Commit:** `fd9d5b0`
**Files:** `contracts/script/TransferRestraintAdmin.s.sol`,
`docs/RUNBOOK_MULTISIG_ADMIN.md`
**Adds:** Foundry script that grants admin/restraint roles to a Gnosis
Safe and revokes the deployer key. Step-by-step runbook for Arc.

### A.5 · Prometheus + Grafana stack
**Commit:** `b2949c5`
**Files:** `services/boule/src/boule/metrics.py`,
`infra/prometheus/prometheus.yml`, `infra/grafana/...`,
`docker-compose.yml`
**Adds:** Nine Prometheus metrics (deliberations, costs, restraints,
drift, council diversity, equity, open positions). Provisioned Grafana
dashboard at `:3001` (admin / pantheon).
**Upstream:** prometheus-client, Prometheus, Grafana (Apache 2.0).

---

## Tier B — Execution quality

### B.6 · Drawdown-adjusted Kelly
**Commit:** `02fd6f7`
**Module:** `services/areopagus/src/areopagus/drawdown.py`
**Adds:** Clamped linear ramp `1.0 → floor (0.2)` at the configured
DD cap (30%). New `DRAWDOWN_FLOOR` rejection path when the haircut
pushes sizing below the Kelly minimum.

### B.7 · Walk-forward calibration
**Commit:** `0da2ba4`
**Module:** `services/ostrakon/src/ostrakon/agent_calibration.py`
**Adds:** `calibrate_from_csv_windowed(window_days)` and
`calibrate_from_csv_decayed(half_life_days)` with `sample_weight`
plumbed through Platt + isotonic CV. CLI flags `--window-days` /
`--half-life-days` on the `ostrakon calibrate` subcommand.

### B.8 · Argos resolution-lag state machine
**Commit:** `5b1ae97`
**Module:** `services/argos/src/argos/resolution_lag.py`
**Adds:** `OPEN → RESOLVING → STUCK / RESOLVED` state machine. Retracts
walk back to OPEN. `stuck_trades()` accessor for oncall alerts. New
Redis stream `argos:resolution_lag`.

### B.9 · Maker/taker execution mode
**Commit:** `52c8b8d`
**Module:** `services/strategos/src/strategos/execution_mode.py`
**Adds:** `choose_execution(...)` conservatively returns taker (default)
and only promotes to maker when not urgent, not high-conviction,
size/depth < 10%, and the resulting price isn't at the unit edge.

### B.10 · Online slippage learner
**Commit:** `d596ceb`
**Module:** `services/strategos/src/strategos/slippage_learner.py`
**Adds:** Per-(market, log10 depth bucket) EWMA of realised − predicted
slippage. Refines `estimate_slippage` on each fill. JSON persist
+ load for restart continuity.

---

## Tier C — Intelligence

### C.11 · RAG over resolved markets
**Commit:** `13bb15d`
**Module:** `services/apollo/src/apollo/rag/`
**Adds:** `VectorStore` Protocol with two implementations:
`InMemoryVectorStore` (pure-Python cosine + hashed-bag embedding,
default) and `ChromaVectorStore` (lazy chromadb import, persistent on
disk). Production pairing: chromadb + sentence-transformers
`all-MiniLM-L6-v2`.
**Upstream:** ChromaDB (Apache 2.0), sentence-transformers (Apache 2.0).

### C.12 · Eris adversarial agent
**Commit:** `17031e9`
**Files:** `services/boule/src/boule/agents/adversarial.py`,
`services/boule/src/boule/prompts/eris.md`,
`services/boule/src/boule/debate.py`
**Adds:** Eris reads the round-1 transcript, infers the council's lean
(APPROVE/REJECT/BUY/SELL token counts), and builds the strongest
counter-case. Opt-in via `BOULE_ERIS_ENABLED=1`.

### C.13 · Reflection-driven prompt evolution
**Commit:** `d318b0a`
**Module:** `services/underworld/src/underworld/prompt_evolver.py`
**Adds:** `propose_edits(broken_assumptions_by_agent)` promotes repeated
post-mortem patterns into prompt edits. `apply_edit` appends a
marker-delimited `## Lessons Learned` block to the agent's prompt file.
Idempotent + merge-into-existing-block aware.

### C.14 · Agent ablation
**Commit:** `aaebf7e`
**Module:** `services/ostrakon/src/ostrakon/ablation.py`
**Adds:** `ablate_from_csv` computes `delta_X = brier_without_X −
brier_all` per agent. Positive = agent helps; negative = retire.
`ostrakon ablate` CLI subcommand.

### C.15 · Nitter crowd sentiment
**Commit:** `c5ef08b`
**Modules:** `services/apollo/src/apollo/sources/nitter.py`,
`services/apollo/src/apollo/features/crowd_sentiment.py`
**Adds:** RSS scraper for Nitter (open X front-end). VADER-compatible
in-tree lexicon scorer with negation + intensifier handling.
**Upstream:** Nitter (AGPL on the server side, but we're a client).

---

## Tier D — Venues + data

### D.16 · Kalshi connector
**Commit:** `4665e97`
**Module:** `services/pythia/src/pythia/kalshi.py`
**Adds:** Read-only Kalshi REST adapter — events, markets, orderbook,
mid price normalised from cents to `[0, 1]`. `map_to_pantheon_market`
normalises the Kalshi market shape to match Polymarket.

### D.17 · DeFiLlama on-chain + TVL feature
**Commit:** `9cece5d`
**Modules:** `services/pythia/src/pythia/defillama.py` (extended),
`services/apollo/src/apollo/features/onchain_tvl.py`
**Adds:** Extended DeFiLlama with `chains()`, `chain_tvl()`,
`stablecoin_snapshot()`, `stablecoin_total_marketcap()`, `pool_yields()`.
Apollo feature: log-scaled + percentile-rank TVL score.

### D.18 · TradingView screener
**Commit:** `167e27f`
**Module:** `services/pythia/src/pythia/tradingview.py`
**Adds:** Lazy adapter around `tradingview-screener` PyPI package.
Ships three preset specs (oversold, overbought, trend breakout).
**Upstream:** tradingview-screener (MIT).

### D.19 · News headline NER + market matcher
**Commit:** `1266685`
**Module:** `services/apollo/src/apollo/features/news_ner.py`
**Adds:** Two-path entity extraction (spaCy via `find_spec` lazy
detection; regex fallback for capitalised sequences + tickers).
Token-overlap matcher returns markets above a configurable threshold.
**Upstream:** spaCy (MIT).

---

## Tier E — Operational maturity

### E.20 · Alembic async migrations
**Commit:** `018f018`
**Files:** `apps/api/alembic.ini`, `apps/api/migrations/`
**Adds:** Async-aware Alembic environment that reads the database URL
from `pantheon_api.config.settings`. Operator runbook in
`apps/api/migrations/README.md`. Empty first revision generated by
the operator against an actual DB (`alembic revision --autogenerate`).
**Upstream:** Alembic (MIT).

### E.21 · Hourly Postgres + Redis backup
**Commit:** `f502a1e`
**Files:** `infra/backup/*`, `docker-compose.yml`
**Adds:** New compose service that runs `pg_dump` and Redis `BGSAVE`
every `BACKUP_INTERVAL_SECONDS` (default 3600) and prunes files older
than `BACKUP_RETENTION_DAYS` (default 14).

### E.22 · SOPS + age secrets
**Commit:** `a9dd1dc`
**Files:** `.sops.yaml`, `scripts/decrypt-env.sh`, `infra/secrets/README.md`
**Adds:** Mozilla SOPS rules for `.env.enc` and `infra/secrets/*.yaml`.
Decrypt-on-compose-up helper. Per-operator age key generation and
rotation runbook.
**Upstream:** SOPS (MPL-2.0), age (BSD).

### E.23 · slowapi rate limiting
**Commit:** `b914be7`
**Module:** `apps/api/src/pantheon_api/middleware/rate_limit.py`
**Adds:** Global IP-keyed rate limit (default 120/minute + 30/second
burst) backed by Redis when `REDIS_URL` is set. Headers enabled so
clients back off before 429.
**Upstream:** slowapi (MIT).

### E.24 · Deep health probes
**Commit:** `f601638`
**Module:** `apps/api/src/pantheon_api/routers/health.py`
**Adds:** `GET /health/deep` returns per-probe ProbeResults (Redis info,
DB version, RPC chainId, IPFS id) under per-probe + total time budgets.

---

## Tier F — Frontend

### F.25 · Pure-SVG Sankey for trace flow
**Commit:** `3754291`
**Files:** `apps/web/components/charts/sankey.tsx`,
`apps/web/lib/trace-sankey.ts`
**Adds:** Zero-dep Sankey component. `buildTraceSankey(events)` projects
a Boule TraceEvent stream into `{ nodes, links }` with one node per
(round, agent) plus APPROVE / REJECT / ABSTAIN sinks.

### F.26 · Line + bar charts + perf metrics
**Commit:** `b50afe5`
**Files:** `apps/web/components/charts/line.tsx`,
`apps/web/components/charts/bar.tsx`,
`apps/web/lib/perf-metrics.ts`
**Adds:** Pure-SVG line + bar primitives. `dailyBars`, `rollingSharpe`,
`maxDrawdown`, and `scorecard` helpers for the `/dashboard` route.

### F.27 · Trade-approval card
**Commit:** `7aacd7d`
**File:** `apps/web/components/trade-approval-card.tsx`
**Adds:** Manual approval UI for the first-N gate. Keyboard shortcuts
`a` (approve) / `r` (reject) / `e` (edit size). Reject requires ≥ 3
characters of justification.

### F.28 · Agent leaderboard
**Commit:** `ca1ceda`
**File:** `apps/web/components/agent-leaderboard.tsx`
**Adds:** Brier-ranked table with sortable columns, Brier mini-bar
visualization, and sign-coloured 30-day credibility delta.

---

## Tier G — Safety hygiene

### G.29 · mutmut mutation testing
**Commit:** `04123b8`
**Files:** `infra/quality/MUTATION_TESTING.md`, `justfile`
**Adds:** Targeted mutation-testing scaffold covering the six financial
modules (`kelly`, `drawdown`, `correlation_sizing`, `slippage`,
`execution_mode`, `slippage_learner`). Justfile targets `just mutmut`
/ `mutmut-results` / `mutmut-show`.
**Upstream:** mutmut (BSD).

### G.30 · Toxiproxy chaos
**Commit:** `344149c`
**Files:** `infra/chaos/*`, `docker-compose.yml`
**Adds:** Toxiproxy sidecar (gated by `chaos` compose profile) +
six declarative scenarios (baseline, redis latency, redis packet loss,
postgres slow, rpc flaky, catastrophe). Justfile targets
`chaos-up` / `chaos-down`.
**Upstream:** Toxiproxy (MIT).

### G.31 · Halmos symbolic verification
**Commit:** `10e4846`
**Files:** `contracts/test/ProofOfRestraintSymbolic.t.sol`,
`contracts/test/PantheonConstitutionSymbolic.t.sol`,
`infra/quality/FORMAL_VERIFICATION.md`
**Adds:** Halmos `check_*` specs for monotonicity, record integrity,
role-gated writes, input validation, soft-cap-tighter-than-hard
invariants, and signal-acceptance monotonicity. Runs in CI alongside
Foundry.
**Upstream:** Halmos (MIT).

### G.32 · IRS Form 8949 tax export
**Commit:** `c10f477`
**Module:** `services/ostrakon/src/ostrakon/tax_export.py`
**Adds:** `to_csv_rows` / `write_csv` / `summary` for short-vs-long-term
aggregation. Cancelled trades dropped. Year-range computation handles
single-year and multi-year exports.
