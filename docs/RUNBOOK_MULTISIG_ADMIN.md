# Runbook: Migrate ProofOfRestraint admin to Gnosis Safe

The flagship `ProofOfRestraint` contract on Arc Testnet was deployed with a single-key deployer (the EOA in `PRIVATE_KEY`). That deployer holds both `DEFAULT_ADMIN_ROLE` and `RESTRAINT_ROLE`. For production we want a Gnosis Safe (or any multisig) to be the sole admin.

This runbook walks through the migration with **zero downtime** for restraint writes.

## Prerequisites

1. Deployed `ProofOfRestraint` on Arc Testnet at `0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895`.
2. A funded Gnosis Safe on Arc with at least 2 signers (e.g., 2-of-3).
3. The deployer wallet still holds both roles (un-modified since deploy).
4. `forge` 1.4 or newer.
5. `PRIVATE_KEY` exported in env, sufficient ETH for gas (≈ $0.0001 of test USDC).

## Step 1 — Verify current role state

```bash
cast call 0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895 \
    'hasRole(bytes32,address)(bool)' \
    0x0000000000000000000000000000000000000000000000000000000000000000 \
    $DEPLOYER_ADDRESS \
    --rpc-url https://rpc.testnet.arc.network
```

Expect `true`. Repeat for `RESTRAINT_ROLE` (`keccak256("RESTRAINT_ROLE")`).

## Step 2 — Migrate admin roles

```bash
forge script contracts/script/TransferRestraintAdmin.s.sol:TransferRestraintAdmin \
    --rpc-url https://rpc.testnet.arc.network \
    --broadcast \
    --sig "run(address,address)" \
    0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895 \
    $GNOSIS_SAFE_ADDRESS
```

The script in order:
1. **Grants** `DEFAULT_ADMIN_ROLE` to the Safe.
2. **Grants** `RESTRAINT_ROLE` to the Safe.
3. **Revokes** `RESTRAINT_ROLE` from the deployer.
4. **Revokes** `DEFAULT_ADMIN_ROLE` from the deployer.

Order matters — if revocation happened first the contract would be admin-less and unrecoverable.

## Step 3 — Verify deployer no longer has roles

```bash
# Should print false for both
cast call 0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895 \
    'hasRole(bytes32,address)(bool)' \
    0x0000000000000000000000000000000000000000000000000000000000000000 \
    $DEPLOYER_ADDRESS \
    --rpc-url https://rpc.testnet.arc.network
```

## Step 4 — Update Areopagus chain writer

The Areopagus consumer that writes `declineTrade(...)` must now sign with a key the Safe trusts (a Safe-owned EOA via module, or proxied via a relayer the Safe approves).

Two viable paths:

**Path A — Safe Module Pattern (recommended).** Deploy a thin `RestraintAnchor` module that the Safe enables. The module exposes a single function `anchor(bytes32 signalHash, string marketId, string reasonCode, string note)` that the Areopagus EOA can call. The module then calls `ProofOfRestraint.declineTrade` with the Safe as `msg.sender`.

**Path B — Direct Safe Owner.** Make the Areopagus key one of the Safe's owners with a threshold of 1 for this specific call. Less secure; not recommended for production but acceptable for testnet.

For Arc Testnet demo, Path B is fine. For mainnet, build the module.

## Step 5 — Rotate the original deployer key

Once admin migration is confirmed:

1. Generate a new EOA for any further deploys.
2. Move ETH/USDC from the old deployer to the new one.
3. Update `.env`'s `PRIVATE_KEY` value to the new key.
4. Restart any service that read `PRIVATE_KEY` (Areopagus consumer, deploy CI).
5. The compromised-or-old key is now irrelevant — it has no privileged on-chain authority.

## Rollback

If something goes wrong before Step 4, the original deployer **still has admin** (the script grants then revokes; if the script reverted mid-way, only the grants landed). Re-run the script with `--resume` after fixing the issue.

After Step 4 there is no rollback path other than the Safe granting `DEFAULT_ADMIN_ROLE` to a recovery account.

## Verification on Arcscan

After the migration tx confirms, the contract's "Read Contract" tab on Arcscan should show:

- `hasRole(0x00, deployer)` → false
- `hasRole(0x00, safe)` → true
- `hasRole(RESTRAINT_ROLE, deployer)` → false
- `hasRole(RESTRAINT_ROLE, safe)` → true

`getRoleAdmin(RESTRAINT_ROLE)` is still `DEFAULT_ADMIN_ROLE`, which the Safe now holds.
