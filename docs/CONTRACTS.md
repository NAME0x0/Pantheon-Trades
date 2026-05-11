# Smart Contracts

All contracts deployed on Arc Testnet (Chain ID: 5042002).

See `docs/ARC_INTEGRATION.md` for network details.
See `docs/FOUNDRY_SETUP.md` for build and deployment.

## Contract Inventory

### Core Trading

| Contract | File | Purpose |
|----------|------|---------|
| `PantheonTrades` | `src/PantheonTrades.sol` | Main coordinator contract |
| `ThesisRegistry` | `src/ThesisRegistry.sol` | Immutable thesis records |
| `SignalRegistry` | `src/SignalRegistry.sol` | Signal band records |
| `TradeProof` | `src/TradeProof.sol` | Proof of executed trades |
| `ExecutionVault` | `src/ExecutionVault.sol` | Execution record storage |
| `DecisionCourt` | `src/DecisionCourt.sol` | Veto and decision records |
| `StakingVault` | `src/StakingVault.sol` | Strategy capital staking |

### Restraint and Counterfactual

| Contract | File | Purpose |
|----------|------|---------|
| `ProofOfRestraint` | `src/ProofOfRestraint.sol` | No-trade proofs |
| `NoTradeAlpha` | `src/NoTradeAlpha.sol` | Counterfactual PnL tracking |
| `CounterfactualOracle` | `src/CounterfactualOracle.sol` | Counterfactual resolution |

### Agent Identity (ERC-8004)

| Contract | File | Purpose |
|----------|------|---------|
| `AgentPassport` | `src/AgentPassport.sol` | Unified agent passport |
| `AgentReputation` | `src/AgentReputation.sol` | Reputation accumulation |
| `IdentityRegistry` | `src/erc8004/IdentityRegistry.sol` | ERC-8004 identity |
| `ReputationRegistry` | `src/erc8004/ReputationRegistry.sol` | ERC-8004 reputation |
| `ValidationRegistry` | `src/erc8004/ValidationRegistry.sol` | ERC-8004 audits |

### Lifecycle

| Contract | File | Purpose |
|----------|------|---------|
| `StrategyLifecycle` | `src/StrategyLifecycle.sol` | Strategy state machine |
| `GoalsBoard` | `src/GoalsBoard.sol` | Goal completion records |
| `Elysium` | `src/Elysium.sol` | Simulation result records |
| `Underworld` | `src/Underworld.sol` | Post-mortem records |
| `Olympus` | `src/Olympus.sol` | Governance state |

### Governance

| Contract | File | Purpose |
|----------|------|---------|
| `PantheonConstitution` | `src/PantheonConstitution.sol` | Immutable system rules |
| `ZeusMultisig` | `src/governance/ZeusMultisig.sol` | Multi-sig governance |
| `EmergencyPause` | `src/governance/EmergencyPause.sol` | Circuit breaker |
| `RoleManager` | `src/governance/RoleManager.sol` | Access control |

### Archive

| Contract | File | Purpose |
|----------|------|---------|
| `Parthenon` | `src/Parthenon.sol` | Merkle root anchoring |
| `Ostrakon` | `src/Ostrakon.sol` | On-chain scoring records |

### Libraries

| Library | File | Purpose |
|---------|------|---------|
| `Bands` | `src/libs/Bands.sol` | Signal band constants |
| `Hashing` | `src/libs/Hashing.sol` | Content hashing utilities |
| `Roles` | `src/libs/Roles.sol` | Role constant definitions |

## Non-Upgradeable Contracts

Per Constitution Article X:
- `PantheonConstitution.sol`
- `ThesisRegistry.sol`
- `TradeProof.sol`
- `ProofOfRestraint.sol`

All other contracts are upgradeable behind `ZeusMultisig` proxy pattern.

## Deployment Scripts

```bash
# Deploy all contracts
cd contracts
forge script script/DeployPantheon.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast

# Deploy ERC-8004 registries
forge script script/DeployERC8004.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast

# Deploy governance (ZeusMultisig, EmergencyPause)
forge script script/DeployGovernance.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast

# Deploy restraint contracts
forge script script/DeployRestraint.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast
```
