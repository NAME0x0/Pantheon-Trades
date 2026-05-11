# Foundry Setup

## Prerequisites

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install Canteen Arc CLI
uv tool install git+https://github.com/the-canteen-dev/ARC-cli.git

# Get Arc RPC URL
arc-canteen login
arc-canteen rpc-url --export  # add to shell rc
```

## Environment

Copy `contracts/.env.example` to `contracts/.env`:
```bash
ARC_TESTNET_RPC_URL=https://rpc.testnet.arc-node.thecanteenapp.com/v1/<your-key>
PRIVATE_KEY=0x...  # Deployer private key (use a test key, not production)
ARC_CHAIN_ID=5042002
```

## Building

```bash
cd contracts
forge build
```

## Testing

```bash
# Run all tests
forge test

# Run with verbosity
forge test -vvv

# Run specific test
forge test --match-contract ThesisRegistryTest -vvv

# Coverage report
forge coverage
```

## Deployment

```bash
# Deploy all contracts (dry run)
forge script script/DeployPantheon.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY

# Deploy with broadcast
forge script script/DeployPantheon.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast

# Verify on block explorer
forge verify-contract $CONTRACT_ADDRESS src/ThesisRegistry.sol:ThesisRegistry --chain-id 5042002
```

## Contract Addresses

After deployment, addresses are written to `contracts/broadcast/Deploy.s.sol/{chainId}/run-latest.json`.

Copy deployed addresses to service `.env` files:
- `THESIS_REGISTRY_ADDRESS`
- `AGENT_REPUTATION_ADDRESS`
- `TRADE_PROOF_ADDRESS`
- etc.

## Remappings

`contracts/remappings.txt` defines import paths. Add new dependencies here.

## Foundry Config

`contracts/foundry.toml` — optimizer settings, test configuration.

## Gas Report

```bash
forge test --gas-report
```

Target: all critical path functions < 150,000 gas.

## Solidity Version

Solidity 0.8.x (latest stable). All contracts pin to specific minor version in pragma.

## Block Explorer

Arc Testnet explorer: https://testnet.arcscan.app

Use to verify deployments and inspect contract state.
