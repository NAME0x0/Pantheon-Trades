# Pantheon Trades — Claude Code Instructions

## Project

AI prediction market trading system. Multi-agent council of Greek-god-named agents debates trades before execution on Polymarket CLOB. Everything is traced, archived on-chain, and scored.

## Monorepo

pnpm workspaces + Turborepo. Python services use uv. Never mix pip with uv.

```bash
pnpm install          # install all JS deps
pnpm dev              # start all apps in dev mode
pnpm test             # run all tests
cd contracts && forge test   # Solidity tests
```

## Python Services

Each service under `services/` and `apps/api/` uses uv:
```bash
cd services/boule && uv run pytest
cd services/apollo && uv run python -m apollo.cli
```

## Key Conventions

- Signals: typed Pydantic models, always validated at source (Pythia)
- Theses: structured JSON following `docs/THESIS_SCHEMA.md`
- Traces: every Boule run emits a `TraceEvent` per agent step — see `docs/TRACE_FORMAT.md`
- Risk policy: all position limits live in `docs/RISK_POLICY.md` and enforced by Areopagus
- No trade without Areopagus approval
- Every archive op goes through Parthenon — no direct IPFS calls from other services
- Agent prompts are Markdown files in `services/boule/src/boule/prompts/`

## Services Port Map

| Service | Port |
|---------|------|
| api (FastAPI) | 8000 |
| apollo | 8001 |
| boule | 8002 |
| areopagus | 8003 |
| strategos | 8004 |
| argos | 8005 |
| ostrakon | 8006 |
| parthenon | 8007 |
| pythia | 8008 |
| elysium | 8009 |
| underworld | 8010 |
| moirai | 8011 |
| olympus | 8012 |
| web (Next.js) | 3000 |

## Environment

Copy `.env.example` files before running. Required vars:
- `ANTHROPIC_API_KEY` — Claude API for agent intelligence
- `POLYMARKET_API_KEY` — CLOB trading
- `DATABASE_URL` — PostgreSQL
- `REDIS_URL` — pub/sub and cache
- `IPFS_API_URL` — IPFS node
- `IRYS_KEY` — Irys bundler for permanent storage
- `PRIVATE_KEY` — Polygon wallet for on-chain ops
- `RPC_URL` — Polygon RPC

## Docs Index

Full design docs are in `docs/`. Key entry points:
- `docs/ARCHITECTURE.md` — system design
- `docs/AGENTS.md` — agent roster
- `docs/CONSTITUTION.md` — immutable system rules
- `docs/SIGNAL_SPEC.md` — signal schema
- `docs/THESIS_SCHEMA.md` — thesis structure
- `docs/RISK_POLICY.md` — position limits and gates
- `docs/TRACE_FORMAT.md` — trace event schema
- `docs/SETTLEMENT_FLOW.md` — on-chain settlement
- `docs/MOIRAI_LAWS.md` — lifecycle rules

## Never Do

- Never bypass Areopagus to submit a trade directly
- Never write to IPFS directly — route through Parthenon
- Never hardcode private keys or API keys
- Never commit `.env` files
- Never modify `PantheonConstitution.sol` after deployment — it is immutable by design
