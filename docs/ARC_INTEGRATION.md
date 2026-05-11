# Arc Integration

## Arc Testnet RPC

Operated by Canteen. Public JSON-RPC node built for agentic use.

### Network details

| Field | Value |
|---|---|
| Network | Arc Testnet |
| Chain ID | 5042002 |
| Currency symbol | USDC |
| RPC URL | `https://rpc.testnet.arc-node.thecanteenapp.com/v1/<key>` |
| Block explorer | https://testnet.arcscan.app |

### Getting an RPC key

The `<key>` in the RPC URL is issued per developer. Install the Canteen CLI and sign in with your GitHub handle:

```bash
uv tool install git+https://github.com/the-canteen-dev/ARC-cli.git
arc-canteen login
```

Print personal RPC URL (with key embedded), or export as `$RPC`:

```bash
arc-canteen rpc-url            # print https://rpc.testnet.arc-node.thecanteenapp.com/v1/<key>
arc-canteen rpc-url --export   # eval-able: export RPC=...
arc-canteen shell-init         # rc snippet that auto-loads $RPC
```

Fire JSON-RPC calls straight from CLI without wiring up a client:

```bash
arc-canteen rpc eth_blockNumber
arc-canteen rpc eth_chainId
```

### Agent context: docs & working Arc examples

CLI doubles as context provider for coding agents. Dumps `AGENTS.md` with paths, syncs developer docs for Arc + Circle alongside runnable sample codebases (from `the-canteen-dev/context-arc`):

```bash
arc-canteen context        # print AGENTS.md + paths to docs and samples
arc-canteen context sync   # clone/pull docs + Arc example repos into ~/.arc-canteen/context/
```

Point coding agent at `~/.arc-canteen/context/` for Arc/Circle docs + real example projects. Re-run `context sync` to pull latest.

### Product & traction updates

Same CLI records progress — no separate dashboard:

```bash
arc-canteen update product     # submit product update
arc-canteen update traction    # submit traction update
arc-canteen status             # dashboard
arc-canteen ls                 # list past updates
```

---

## Pantheon Trades usage

- `packages/hermes/` → wraps RPC + provider failover + contract calls + USDC + Paymaster + Gateway + indexer + event listener
- `services/parthenon/anchor.py` → posts reasoning-trace hashes onchain
- `services/parthenon/erc8004_client.py` → wraps ERC-8004 agent identity/reputation/validation registries
- `contracts/` → PantheonTrades, SignalRegistry, ThesisRegistry, DecisionCourt, AgentReputation, AgentPassport, ProofOfRestraint, NoTradeAlpha, CounterfactualOracle, GoalsBoard, StrategyLifecycle, PantheonConstitution, Underworld, Elysium, Olympus, Ostrakon, Parthenon, TradeProof, StakingVault, ExecutionVault, ZeusMultisig, EmergencyPause + ERC-8004 (IdentityRegistry, ReputationRegistry, ValidationRegistry)
- Env: see `.env.example` for `ARC_RPC_URL`, `ARC_CHAIN_ID`, `ARC_EXPLORER_URL`, plus `contracts/.env.example` for Foundry deploy (`ARC_TESTNET_RPC_URL`, `PRIVATE_KEY`)
- Foundry workflow: `forge build && forge test && forge script script/DeployPantheon.s.sol --rpc-url $ARC_TESTNET_RPC_URL --private-key $PRIVATE_KEY --broadcast`
