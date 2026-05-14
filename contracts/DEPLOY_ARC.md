# Deploy to Arc Testnet

> **Live deployment (2026-05-14)** — see `deployments/arc-testnet.json`:
> - PantheonConstitution: [`0xA9cdB1F40f31e683184555b856F252456544e4fd`](https://testnet.arcscan.app/address/0xA9cdB1F40f31e683184555b856F252456544e4fd)
> - ThesisRegistry: [`0x3bcD258187aDB614b3f45c4b54df7482928bc800`](https://testnet.arcscan.app/address/0x3bcD258187aDB614b3f45c4b54df7482928bc800)
> - End-to-end `anchor()` verified, both Merkle proofs return `true` on-chain.
> - Total cost: 0.033 USDC.


End-to-end guide for putting `PantheonConstitution` and `ThesisRegistry`
on Arc Testnet (chain id 5042002). Everything in this guide except the
actual broadcast has been dry-run against the live RPC.

## 1. Prereqs

- Foundry installed (`foundryup` / `forge --version`).
- `lib/forge-std` and `lib/openzeppelin-contracts` present (already
  vendored via `forge install`).
- An EVM wallet with a private key you control.
- Arc Testnet USDC in that wallet (Arc uses USDC as native gas).

## 2. Get USDC from the faucet

The faucet hands out test USDC on Arc Testnet.

1. Open <https://faucet.circle.com>.
2. Pick **Arc Sepolia / Arc Testnet** in the network selector.
3. Paste the address you intend to deploy from.
4. Submit. Funds land in the wallet within ~1 minute.

Verify the balance with `cast`:

```bash
cast balance <YOUR_ADDRESS> --rpc-url arc_testnet
```

Native balance is denominated in 18-decimal USDC. Anything above
`100000000000000000` (0.1 USDC) is plenty for both deploys; the
dry-run estimated `0.079 USDC` total.

## 3. (Optional) Install Circle's Claude Code skills

These are guided workflows for Arc / USDC / Circle Smart Contract
Platform. They are independent of the deploy itself but useful next
steps once contracts are live.

```text
/plugin marketplace add circlefin/skills
/plugin install circle-skills@circle
```

After install you get `use-arc`, `use-usdc`, `use-circle-wallets`,
`use-developer-controlled-wallets`, `bridge-stablecoin`, and
`use-smart-contract-platform` skills in Claude Code.

## 4. Compile + test locally

```bash
cd contracts
forge build
forge test --match-path "test/{PantheonConstitution,ThesisRegistry}.t.sol" -vv
```

Expected: 21 tests pass.

## 5. Dry-run against the live RPC (no broadcast)

```bash
cd contracts
export PRIVATE_KEY=0x...        # your wallet's key
forge script script/DeployPantheon.s.sol:DeployPantheon \
  --rpc-url arc_testnet \
  -vvv
```

Foundry prints the predicted addresses, the gas estimate, and the
USDC cost. **No transactions are sent yet.**

## 6. Broadcast

Add `--broadcast`. This is the only step that signs and submits
transactions. Make sure the private key has USDC funded.

```bash
cd contracts
export PRIVATE_KEY=0x...
forge script script/DeployPantheon.s.sol:DeployPantheon \
  --rpc-url arc_testnet \
  --broadcast \
  -vvv
```

Foundry prints the actual deployed addresses once both txs confirm.
Save them — they go into your `.env` / production config:

```env
PARTHENON_REGISTRY_ADDRESS=0x...   # ThesisRegistry
PANTHEON_CONSTITUTION=0x...        # PantheonConstitution
RPC_URL=https://rpc.testnet.arc.network
CHAIN_ID=5042002
```

## 7. Sanity-check on-chain

```bash
# Constitution
cast call <CONSTITUTION_ADDRESS> "VERSION()(string)" --rpc-url arc_testnet
cast call <CONSTITUTION_ADDRESS> "CHAIN_ID()(uint64)" --rpc-url arc_testnet
cast call <CONSTITUTION_ADDRESS> "MAX_POSITION_PCT_BPS()(uint16)" --rpc-url arc_testnet

# Registry
cast call <REGISTRY_ADDRESS> "ANCHOR_ROLE()(bytes32)" --rpc-url arc_testnet
cast call <REGISTRY_ADDRESS> \
  "hasRole(bytes32,address)(bool)" \
  $(cast call <REGISTRY_ADDRESS> "ANCHOR_ROLE()(bytes32)" --rpc-url arc_testnet) \
  <YOUR_ADDRESS> --rpc-url arc_testnet
```

Either contract address can also be inspected in the [Arc Testnet
explorer](https://testnet.arcscan.app/).

## 8. Wire the off-chain anchor service

Set the env vars and the Parthenon `AnchorService` picks them up
automatically (see `services/parthenon/src/parthenon/anchor.py`):

```env
PRIVATE_KEY=0x...
RPC_URL=https://rpc.testnet.arc.network
CHAIN_ID=5042002
PARTHENON_REGISTRY_ADDRESS=0x...
```

Validate end-to-end with the existing probe:

```bash
python tests/arc_probe.py
```

That hits the live RPC, reads USDC, round-trips a Signal through the
keccak content hash, and verifies the Anchor / ERC-8004 client configs
construct cleanly.
