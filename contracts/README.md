# Pantheon Contracts

Solidity smart contracts for Pantheon Trades, deployed on Arc Testnet (Chain ID: 5042002).

## Setup

See `docs/FOUNDRY_SETUP.md` for full setup instructions.

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash && foundryup

# Build
forge build

# Test
forge test

# Deploy
cp .env.example .env  # fill in ARC_TESTNET_RPC_URL and PRIVATE_KEY
forge script script/DeployPantheon.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast
```

## Structure

```
src/
  PantheonTrades.sol         Main coordinator
  ThesisRegistry.sol         Immutable thesis records
  SignalRegistry.sol         Signal band records
  TradeProof.sol             Trade execution proofs
  ProofOfRestraint.sol       No-trade proofs
  NoTradeAlpha.sol           Counterfactual tracking
  AgentPassport.sol          Agent identity
  AgentReputation.sol        Reputation accumulation
  StrategyLifecycle.sol      Strategy state machine
  PantheonConstitution.sol   Immutable system rules
  Parthenon.sol              Merkle root anchoring
  Ostrakon.sol               Scoring records
  GoalsBoard.sol             Goal completions
  CounterfactualOracle.sol   Counterfactual results
  Elysium.sol                Simulation records
  Underworld.sol             Post-mortem records
  Olympus.sol                Governance state
  DecisionCourt.sol          Veto records
  ExecutionVault.sol         Execution storage
  StakingVault.sol           Capital staking
  erc8004/
    IdentityRegistry.sol
    ReputationRegistry.sol
    ValidationRegistry.sol
    IERC8004.sol
  governance/
    ZeusMultisig.sol
    EmergencyPause.sol
    RoleManager.sol
  libs/
    Bands.sol
    Hashing.sol
    Roles.sol
  interfaces/                Interface definitions for all contracts

test/                        Foundry test suite
script/                      Deployment and utility scripts
```

## Contract Docs

See `docs/CONTRACTS.md` for full inventory and purpose of each contract.

## Network

- Chain ID: 5042002
- Currency: USDC
- Block explorer: https://testnet.arcscan.app
- RPC: Canteen Arc Testnet (see `docs/ARC_INTEGRATION.md`)
