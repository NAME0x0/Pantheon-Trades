# System Architecture

## Overview

Pantheon Trades is a multi-agent prediction market trading system. A council of specialized AI agents — each embodying a Greek deity archetype — deliberates on every trade before any capital is deployed. Every decision, including the decision not to trade, is cryptographically recorded on-chain.

The system runs on the **Arc Testnet** (Chain ID: 5042002), an EVM-compatible chain operated by Canteen, with USDC as the currency. Polymarket CLOB is the prediction market exchange.

## Design Principles

1. **No single point of trust** — no agent has unilateral trade authority
2. **Auditable by default** — every agent step is traced and archived
3. **Restraint is alpha** — `ProofOfRestraint` makes not-trading a first-class outcome
4. **Lifecycle law** — Moirai enforces strategy lifecycle; no strategy bypasses it
5. **Counterfactual accountability** — Elysium re-simulates every decision after resolution

## Pipeline

```
External Data Sources
        │
        ▼
   ┌─────────┐
   │  Pythia  │  Raw data oracle (Polymarket, crypto, news, DeFiLlama, Reddit)
   └────┬────┘
        │ normalized market snapshots
        ▼
   ┌─────────┐
   │  Apollo  │  Signal generation — edge, liquidity, volatility, catalyst, sentiment
   └────┬────┘
        │ Signal (ranked, band-scored)
        ▼
   ┌─────────┐
   │  Boule   │  Multi-agent council debate
   │  Council │  bull / bear / technical / news / sentiment / risk / execution / auditor
   └────┬────┘
        │ Thesis (signed council output)
        ▼
   ┌────────────┐
   │ Areopagus  │  Hard risk gates — Kelly sizing, drawdown limits, invalidation checks
   └─────┬──────┘
         │ approved Thesis or rejection
         ▼
   ┌──────────┐
   │ Strategos │  CLOB execution — live or paper routing, slippage estimation
   └─────┬─────┘
         │ Trade submitted
         ▼
   ┌───────┐
   │ Argos  │  Position monitoring — PnL, exit logic, stop adjustments
   └───┬───┘
       │ outcome
       ▼
   ┌──────────┐     ┌────────────┐     ┌──────────┐
   │ Ostrakon  │     │ Parthenon  │     │  Elysium  │
   │ (scoring) │     │ (archive)  │     │(backtest) │
   └──────────┘     └────────────┘     └──────────┘
```

## Service Responsibilities

### Pythia — Data Oracle
- Polls Polymarket CLOB for market snapshots, orderbook depth, recent trades
- Fetches crypto prices, on-chain data from DeFiLlama
- Ingests news from Bloomberg, CoinDesk, Reddit
- Tracks Hyperliquid positioning
- Manages cache, rate limits, staleness sentinels, source trust scores

### Apollo — Signal Engine
- Computes edge score per market (probability mispricing vs. oracle consensus)
- Scores liquidity depth, volatility regime, catalyst proximity
- Sentiment and correlation features
- Assigns markets to signal bands (S, A, B, C, D)
- Filters noise; only S/A bands proceed to Boule

### Boule — Deliberation Council
- Spawns parallel agent workers for each council role
- Runs structured debate in rounds: opening → challenge → synthesis → vote
- Each agent writes a `ThesisBlock` signed with its role
- Swarm produces final `Thesis` with confidence, position size recommendation, and exit conditions
- Full trace emitted per debate

### Areopagus — Risk Court
- Validates thesis against hard policy limits (see `docs/RISK_POLICY.md`)
- Applies Kelly criterion for position sizing
- Checks open drawdown, max exposure, correlation limits
- Invalidation: rejects if oracle staleness, market liquidity, or conflict-of-interest flags triggered
- Issues `ApprovalToken` or `RejectionRecord`

### Strategos — Execution
- Routes approved thesis to live CLOB or paper trading based on strategy mode
- Estimates slippage, latency, fill probability
- Submits limit orders to Polymarket CLOB
- Emits `Trade` event on fill

### Argos — Monitor
- Watches all open positions at configurable intervals
- Calculates real-time PnL
- Triggers exits on: target hit, stop-loss, invalidation event, Areopagus override
- Adjusts stops on partial fills

### Ostrakon — Scoring
- Brier score for probability calibration
- Sharpe ratio per agent per rolling window
- Leaderboard updated after every resolution
- Reward weights fed back to Boule as agent credibility scores

### Parthenon — Archive
- IPFS pinning for all signals, theses, traces, outcomes
- Irys bundler for permanent storage guarantees
- Local fast lookup
- Merkle tree over daily archives, root anchored on-chain via `anchor.py`
- ERC-8004 agent passport read/write via `erc8004_client.py`
- Replay protection: deduplicates archive writes by content hash

### Elysium — Simulation
- Backtests historical theses against resolved outcomes
- Counterfactual oracle: for every no-trade decision, simulates what would have happened
- Paper arena: runs live deliberations in shadow mode without capital
- Overfit detector: flags strategies with suspicious backtest vs. live divergence

### Underworld — Failure Analysis
- Graveyard: storage for terminated strategies
- Post-mortem runner: structured analysis of failed theses
- Hallucination log: catches agent assertions that contradict observable facts
- Broken assumptions tracker: catalogs which prior beliefs failed and why
- Lessons extractor: surfaces lessons back to Boule memory

### Moirai — Lifecycle
- Clotho: strategy creation and registration
- Lachesis: strategy-to-market assignment and threading
- Atropos: strategy termination and archival
- Constitution enforcer: checks all transitions against `docs/MOIRAI_LAWS.md`

### Olympus — Governance
- System state machine: standby / active / degraded / paused / recovery
- Goals board: tracks and enforces daily/weekly objectives
- Adversarial mode: red-team testing of Boule by adversarial agents
- Lifecycle coordinator: promotes/exiles agents based on Ostrakon scores
- Emergency pause: propagates kill switch across all services

## Data Contracts

All inter-service messages are typed Pydantic models. Key types:

| Type | Produced by | Consumed by |
|------|-------------|-------------|
| `MarketSnapshot` | Pythia | Apollo |
| `Signal` | Apollo | Boule |
| `Thesis` | Boule | Areopagus |
| `ApprovalToken` | Areopagus | Strategos |
| `Trade` | Strategos | Argos, Parthenon |
| `ExitSignal` | Argos | Strategos |
| `ScoringRecord` | Ostrakon | Boule (memory) |
| `ArchiveManifest` | Parthenon | On-chain anchor |
| `TraceEvent` | Boule | Parthenon, web UI |

## On-Chain Layer

**Arc Testnet** (Chain ID: 5042002, Currency: USDC). See `docs/ARC_INTEGRATION.md`.

Contracts in `contracts/src/`:

- `ThesisRegistry` — immutable thesis registry, hash + timestamp
- `AgentReputation` — ERC-8004 reputation scores
- `TradeProof` — proof of executed trade
- `ProofOfRestraint` — proof that a signal was observed but trade was declined
- `NoTradeAlpha` — tracks counterfactual value of restraint
- `PantheonConstitution` — immutable system rules (non-upgradeable)
- `ZeusMultisig` — governance multisig for upgradeable contracts
- `EmergencyPause` — cross-contract circuit breaker
- `AgentPassport` — ERC-8004 agent identity

## Storage

| Data | Store |
|------|-------|
| Live state | PostgreSQL |
| Pub/sub events | Redis streams |
| Agent cache | Redis |
| Signal/thesis archive | IPFS (mutable) + Irys (permanent) |
| On-chain anchor | Arc Testnet smart contracts |
| Agent passports | ERC-8004 on Arc Testnet |

## Transport

Services communicate via Redis Streams (async pub/sub). HTTP for synchronous API calls. WebSocket from API gateway to web UI for live signal/trace streaming.

## Security

See `docs/SECURITY.md`, `docs/THREAT_MODEL.md`, `docs/AUTH.md`.

- SIWE (Sign-In With Ethereum) for user authentication
- RBAC for API access (see `docs/RBAC.md`)
- Replay protection on all archive writes
- MEV considerations documented in `docs/MEV_NOTES.md`
