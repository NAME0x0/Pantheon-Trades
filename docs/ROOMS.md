# Rooms

"Rooms" refers to the conceptual spaces where different types of work happen in the system. Useful mental model for onboarding and understanding where to look for things.

## The Agora (Signal Layer)
**Where**: `services/apollo/`, `services/pythia/`
**What happens here**: Market data arrives, gets scored, becomes signals
**Key files**: `apollo/scorer.py`, `apollo/bands.py`, `pythia/polymarket.py`
**When to be here**: Adding new data sources, tuning signal scoring, debugging signal generation

## The Council Chamber (Deliberation)
**Where**: `services/boule/`
**What happens here**: Agent council debates each signal, produces theses
**Key files**: `boule/orchestrator.py`, `boule/swarm.py`, `boule/debate.py`, `boule/prompts/`
**When to be here**: Modifying agent behavior, tuning debate structure, debugging deliberations

## The Court (Risk Gating)
**Where**: `services/areopagus/`
**What happens here**: Theses are validated against risk policy
**Key files**: `areopagus/gates.py`, `areopagus/kelly.py`, `areopagus/policy.py`
**When to be here**: Tuning risk limits, adding new gates, debugging rejections

## The Field (Execution)
**Where**: `services/strategos/`
**What happens here**: Approved theses become real orders on Polymarket CLOB
**Key files**: `strategos/live.py`, `strategos/polymarket_clob.py`, `strategos/slippage.py`
**When to be here**: Order management, slippage tuning, CLOB integration issues

## The Watchtower (Monitoring)
**Where**: `services/argos/`
**What happens here**: Open positions are watched; exits triggered
**Key files**: `argos/monitor.py`, `argos/exits.py`, `argos/pnl.py`
**When to be here**: Exit logic, PnL calculation, stop management

## The Temple (Archive)
**Where**: `services/parthenon/`
**What happens here**: Everything is permanently stored
**Key files**: `parthenon/archive.py`, `parthenon/anchor.py`, `parthenon/erc8004_client.py`
**When to be here**: Storage issues, IPFS pinning, on-chain archival, ERC-8004 passports

## The Voting Hall (Scoring)
**Where**: `services/ostrakon/`
**What happens here**: Agents get scored after each resolution
**Key files**: `ostrakon/brier.py`, `ostrakon/leaderboard.py`, `ostrakon/rewards.py`
**When to be here**: Scoring methodology, leaderboard, agent calibration

## Elysium (Paradise / Simulation)
**Where**: `services/elysium/`
**What happens here**: History replayed, strategies backtested, counterfactuals computed
**Key files**: `elysium/backtest.py`, `elysium/counterfactual.py`, `elysium/paper_arena.py`
**When to be here**: Backtesting, paper trading, strategy evaluation

## The Underworld (Failure Analysis)
**Where**: `services/underworld/`
**What happens here**: Failed theses and strategies are autopsied
**Key files**: `underworld/postmortem.py`, `underworld/lessons.py`, `underworld/hallucination_log.py`
**When to be here**: Understanding why something failed, extracting lessons

## The Fates (Lifecycle)
**Where**: `services/moirai/`
**What happens here**: Strategy lifecycle enforcement
**Key files**: `moirai/clotho.py`, `moirai/lachesis.py`, `moirai/atropos.py`, `moirai/enforcer.py`
**When to be here**: Strategy registration, promotion, termination issues

## Olympus (Governance)
**Where**: `services/olympus/`
**What happens here**: System-level coordination, goals, adversarial testing
**Key files**: `olympus/orchestrator.py`, `olympus/state.py`, `olympus/goals_board.py`
**When to be here**: System health, agent exile, goals configuration

## The Portal (API Gateway)
**Where**: `apps/api/`
**What happens here**: External HTTP/WebSocket traffic handled
**Key files**: `pantheon_api/main.py`, `pantheon_api/routers/`, `pantheon_api/ws/stream.py`
**When to be here**: API changes, authentication, routing

## The Dashboard (Web UI)
**Where**: `apps/web/`
**What happens here**: User-facing interface
**Key files**: `app/(dashboard)/`, `components/`, `hooks/`, `lib/`
**When to be here**: UI features, data visualization, user experience

## The Treasury (Smart Contracts)
**Where**: `contracts/`
**What happens here**: On-chain records, governance, identity
**Key files**: `src/ThesisRegistry.sol`, `src/AgentPassport.sol`, `src/PantheonConstitution.sol`
**When to be here**: Contract features, deployment, on-chain verification
