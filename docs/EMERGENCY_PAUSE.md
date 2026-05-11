# Emergency Pause

The Emergency Pause system allows Pantheon Trades to halt all new trade entries instantly in response to a crisis.

## What Gets Paused

When `EmergencyPause` is activated:
- Apollo stops publishing signals to Boule
- Boule does not start new deliberations
- Areopagus rejects all new `ApprovalToken` requests
- Strategos does not accept new orders
- All pending `ApprovalToken`s are invalidated

What **continues** during pause:
- Argos monitors all open positions
- Argos can still exit positions
- Parthenon continues archiving
- Ostrakon continues scoring resolved markets
- Web UI remains readable

## Activation

### Via ZeusMultisig (2/5 threshold, no timelock)
```bash
# Any 2 signers can activate:
cast send $EMERGENCY_PAUSE_ADDRESS "pause(bytes32)" $REASON --private-key $SIGNER_KEY --rpc-url $ARC_RPC_URL
```

### Via Olympus (automated trigger)
Olympus activates emergency pause automatically on:
- Daily drawdown > 5%
- Weekly drawdown > 8%
- Critical service failure (API, Redis, PostgreSQL all down for > 5 min)
- Detected oracle manipulation (price anomaly score > threshold)

### Via Operator (manual)
Web UI: Admin → Emergency → Pause

Requires admin role JWT + separate on-chain confirmation transaction.

## Resume

Resume requires 3/5 ZeusMultisig approval (higher threshold than pause).

After resuming:
1. Olympus verifies all services are healthy
2. Areopagus re-checks current risk limits (may need drawdown reset)
3. System resumes in paper mode for 1 hour before live mode
4. Human operator confirms live mode activation

## Pause Record

Every pause event is recorded on-chain by `EmergencyPause.sol`:
```solidity
event PauseActivated(address indexed by, bytes32 reason, uint256 timestamp);
event PauseResumed(address indexed by, uint256 timestamp);
```

Archived to Parthenon and visible in the Olympus dashboard.

## Playbook

On discovering a serious issue:

1. **Assess** — Is this an active loss of capital or an operational issue?
2. **Pause** — If yes to either, pause immediately (2 signers)
3. **Stabilize** — Argos manages open positions; no new entries
4. **Investigate** — Identify root cause in Underworld logs
5. **Fix** — Implement fix; run tests
6. **Review** — All signers review the fix
7. **Resume** — 3/5 approval, paper mode first, then live

Target: pause-to-resume < 24 hours for operational issues, < 1 week for complex issues.
