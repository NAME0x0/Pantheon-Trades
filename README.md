<div align="center">

# Pantheon Trades

**A ten-agent AI council debates every prediction-market trade — and anchors every restraint on-chain.**

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

---

## The premise

Most automated trading systems optimize for one number: PnL. They have no notion of *why* a trade is right, no record of trades they refused, and no way for the public to verify their discipline.

Pantheon Trades inverts that. Every signal flows through a structured four-round deliberation between ten Greek-god-named AI agents — bulls argue, bears challenge, risk vetoes, execution sizes. The verdict, whether *trade* or *no trade*, is anchored as a cryptographic witness on Circle's Arc Testnet. Discipline becomes auditable. Restraint becomes alpha.

> **First on-chain restraint witness — recorded live during build:**
> [`0xf9ae0e7b…df960e62ba238e53a828dfa4edb`](https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb) · block `42,337,549` · `onchain_proof_id = 1`

---

## What's distinctive

| | |
|---|---|
| **Ten agents, four rounds** | Bull pair (Ares, Hades), bear pair (Athena, Cassandra), risk triad (Zeus, Solon, Themis), execution triad (Hephaestus, Daedalus, Humans). Openings → challenges → Athena synthesis → blind votes. |
| **Two veto powers** | Zeus and Solon can halt a trade unilaterally on a constitutional violation. Early-veto short-circuits the debate to save tokens. |
| **Half-Kelly with caps** | Areopagus sizes positions using directional edge and a confidence-weighted half-Kelly fraction, then clamps against constitutional position limits and category exposure. |
| **Proof of Restraint** | When the council declines, Areopagus writes a `Restrained(signalHash, marketId, reasonCode, note)` record to a deployed Solidity contract on Arc. The repo's flagship feature is provably live at [`0x4b35…4895`](https://testnet.arcscan.app/address/0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895). |
| **Pluggable LLMs** | `BOULE_LLM_PROVIDER=anthropic` or `gemini`. Provider-specific retry/timeout/throttle logic isolated in `services/boule/src/boule/llm/`. |
| **Portable identities** | ERC-8004 agent passports — councilors carry their reputation across deployments. |

---

## How it works

```
                                  ┌──────────────┐
                                  │   Pythia     │   Polymarket CLOB · price feeds · news · sentiment
                                  └──────┬───────┘
                                         │ raw signal envelope
                                         ▼
                                  ┌──────────────┐
                                  │    Apollo    │   7-dimension scoring → A/B/C edge bands
                                  └──────┬───────┘
                                         │ Signal
                                         ▼
                                  ┌──────────────┐
                                  │    Boule     │   10-agent council, 4 rounds, parallel openings
                                  │   (council)  │   → Athena synthesis → blind votes
                                  └──────┬───────┘
                                         │ Thesis (+ trace events)
                                         ▼
                                  ┌──────────────┐
                                  │  Areopagus   │   constitutional gates · half-Kelly
                                  │   (court)    │   exposure check · drawdown veto
                                  └──┬───────────┘
                                     │
                  ApprovalToken ◄────┤  ────►  RejectionRecord
                         │            │             │
                         ▼            │             ▼
                 ┌─────────────┐      │     ┌───────────────────┐
                 │  Strategos  │      │     │ ProofOfRestraint  │ ──► Arc Testnet
                 │ (CLOB exec) │      │     │     witness       │     contract event
                 └──────┬──────┘      │     └─────────┬─────────┘
                        │             │               │
                        ▼             │               ▼
                 ┌─────────────┐      │     ┌──────────────────┐
                 │    Argos    │      │     │     Parthenon    │   IPFS + Irys + Merkle
                 │  (monitor)  │      │     │    (archive)     │   → on-chain anchor
                 └──────┬──────┘      │     └──────────────────┘
                        │             ▼
                        ▼      ┌─────────────┐
                 ┌─────────────┤   Ostrakon  │   Brier · calibration · Sharpe per agent
                 │  Underworld │  (scoring)  │   → leaderboard + passport updates
                 │ (postmortem)└──────┬──────┘
                 └─────────────┘      │
                                      ▼
                              ┌──────────────┐
                              │   Olympus    │   goals · adversarial mode · exile/promotion
                              │ (coordinator)│
                              └──────────────┘
```

Every box emits structured `TraceEvent`s to Redis. The `/demo` route in the web app replays a captured deliberation event-by-event so you can watch a council form an opinion in real time.

---

## The council

```
            BULL                    BEAR                  RISK             EXECUTION
   ┌───────────────────┐   ┌───────────────────┐   ┌──────────────┐   ┌────────────────┐
   │  Ares             │   │  Athena      ⚙   │   │  Zeus    ⚡  │   │  Hephaestus    │
   │  Hades            │   │  Cassandra        │   │  Solon   ⚡  │   │  Daedalus      │
   │                   │   │                   │   │  Themis      │   │  Humans        │
   └───────────────────┘   └───────────────────┘   └──────────────┘   └────────────────┘
       argues long           argues short             vetoes hard       sizes / routes
                              ⚙ also synthesises      ⚡ veto power
```

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
forge test               18 suites · 51 tests passing · 0 failed
python -m compileall     295 files · 0 syntax errors
pytest sweep             76+ tests across 10 service suites
docker compose config    valid
pnpm install             frozen-lockfile clean
pnpm --filter web build  56 routes · /demo first-load 122 kB
tests/bench.py           every microbenchmark gate green
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

- Full Boule council against live Gemini and Anthropic providers
- Areopagus gating · half-Kelly · constitutional caps
- Strategos paper book execution
- Static demo site on Vercel with interactive council replay
- **Proof of Restraint anchored on Arc Testnet — first witness in [block 42,337,549](https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb)**
- 51/51 Foundry tests · 76+ Python tests · full compose stack healthy

**On the roadmap**

- Live Polymarket CLOB routing (paper mode complete, live mode behind `EXECUTION_MODE=live`)
- Parthenon Merkle batching + Arc anchor cadence tuning
- ERC-8004 passport portability across testnets
- Adversarial-mode strategy retirement via Moirai

---

## License

MIT — see [LICENSE](./LICENSE).
