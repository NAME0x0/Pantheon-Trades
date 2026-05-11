# Zeus Multisig

The ZeusMultisig is the governance mechanism for Pantheon Trades on-chain. It controls all upgradeable contracts, risk policy changes, and emergency actions.

## Configuration

- **Signers**: 5 independent operator addresses
- **Threshold**: 3/5 for standard governance actions
- **Emergency**: 2/5 for emergency pause (speed priority)
- **Timelock**: 72h for all non-emergency actions

Contract: `contracts/src/governance/ZeusMultisig.sol`

## Controlled Actions

| Action | Threshold | Timelock |
|--------|-----------|---------|
| Emergency pause | 2/5 | None |
| Emergency resume | 3/5 | None |
| Risk policy update | 3/5 | 72h |
| Agent prompt upgrade (major) | 3/5 | 72h |
| Agent prompt upgrade (minor) | 2/5 | 24h |
| Contract upgrade | 4/5 | 72h |
| New data source activation | 3/5 | 72h |
| Agent exile confirmation | 3/5 | 24h |
| New signer addition | 4/5 | 72h |
| Signer removal | 4/5 | 72h |

## Proposal Flow

```
1. Admin submits proposal
   ZeusMultisig.propose(target, calldata, description)

2. Signers review during timelock window
   ZeusMultisig.approve(proposalId) -- per signer

3. After timelock + threshold reached
   ZeusMultisig.execute(proposalId)

OR: Any signer can cancel during timelock
    ZeusMultisig.cancel(proposalId)
```

## What Zeus Multisig CANNOT Change

- `PantheonConstitution.sol` — non-upgradeable, immutable
- On-chain records (ThesisRegistry, TradeProof, ProofOfRestraint) — append-only
- Historical archive on IPFS/Irys — permanent by design

## Signer Responsibilities

Each ZeusMultisig signer:
- Holds a hardware wallet (no hot wallets for multisig)
- Reviews every proposal before signing
- Has authority to veto (cancel) malicious proposals
- Is responsible for communicating unavailability so threshold can be maintained

## Signer Rotation

Adding or removing signers requires 4/5 approval + 72h timelock. After rotation, the new configuration is published in this document and on-chain.

## Emergency Pause

The 2/5 emergency pause threshold enables fast response to incidents. After pause:
- All new trade entries blocked
- Open positions continue to be managed by Argos
- Human operators review the incident
- 3/5 approval required to resume

See `docs/EMERGENCY_PAUSE.md`.

## Transparency

All proposals, approvals, and executions are public on Arc Testnet. Block explorer: https://testnet.arcscan.app
