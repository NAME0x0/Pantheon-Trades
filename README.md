# Pantheon Trades

AI-powered prediction market trading system. A council of specialized AI agents named after Greek gods deliberates on every trade, debates the thesis, and votes before any capital moves.

## What It Does

1. **Pythia** ingests raw data — Polymarket CLOB, crypto prices, DeFiLlama, news feeds, Reddit, Hyperliquid
2. **Apollo** filters signals into ranked opportunity bands with edge scores
3. **Boule** convenes the agent council: bull, bear, risk, technical, news, sentiment, execution, and auditor agents debate the thesis in structured rounds
4. **Areopagus** gates the council's verdict against hard risk limits (Kelly, drawdown, invalidation)
5. **Strategos** routes approved theses to live or paper execution on Polymarket CLOB
6. **Argos** monitors open positions and triggers exits
7. **Ostrakon** scores every agent prediction with Brier score, calibration, and Sharpe
8. **Parthenon** archives every signal, thesis, trace, and outcome to IPFS/Irys with Merkle proofs
9. **Elysium** backtests and counterfactual-tests strategies before promotion
10. **Underworld** runs post-mortems on failed theses and logs broken assumptions
11. **Moirai** enforces lifecycle laws — strategy creation (Clotho), assignment (Lachesis), termination (Atropos)
12. **Olympus** governs the whole system: goals board, adversarial mode, agent exile/promotion

Every decision is cryptographically traced, every "no-trade" is proven on-chain via `ProofOfRestraint`, and agent identities are portable ERC-8004 passports.

## Monorepo Layout

```
apps/
  web/          Next.js 14 dashboard
  api/          FastAPI gateway

services/
  apollo/       Signal generation and band scoring
  areopagus/    Risk gating and Kelly sizing
  argos/        Position monitoring and exit logic
  boule/        Multi-agent deliberation council
  elysium/      Backtesting and paper arena
  moirai/       Strategy lifecycle enforcement
  olympus/      System governance and goals
  ostrakon/     Agent scoring and leaderboard
  parthenon/    Archival — IPFS, Irys, Merkle, ERC-8004
  pythia/       Data oracle — Polymarket, news, DeFi
  strategos/    Execution routing — live and paper
  underworld/   Post-mortems and failure analysis

contracts/      Foundry — Polygon smart contracts
docs/           Full design documentation
```

## Quick Start

```bash
# Install deps
pnpm install

# Start all services
docker compose up

# Run tests
pnpm test

# Run Foundry tests
cd contracts && forge test
```

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14, Tailwind CSS, shadcn/ui |
| API gateway | FastAPI, Python 3.12, uv |
| Services | Python 3.12, uv per service |
| AI agents | Anthropic Claude API |
| Contracts | Solidity 0.8.x, Foundry |
| Chain | Arc Testnet (Chain ID: 5042002) |
| Prediction market | Polymarket CLOB |
| Cache | Redis |
| DB | PostgreSQL |
| Archive | IPFS + Irys |
| Monorepo | pnpm + Turborepo |

## Docs

See [`docs/`](./docs/) for full design docs. Start with:
- [Architecture](./docs/ARCHITECTURE.md)
- [Agents](./docs/AGENTS.md)
- [Constitution](./docs/CONSTITUTION.md)
- [Signal Spec](./docs/SIGNAL_SPEC.md)
- [Thesis Schema](./docs/THESIS_SCHEMA.md)
- [Risk Policy](./docs/RISK_POLICY.md)
