# Self-Healing

Pantheon Trades implements several self-healing mechanisms that allow the system to recover from common failures without human intervention.

## Service-Level Self-Healing

### Automatic Retry with Backoff

All external API calls (Anthropic, Polymarket, Arc RPC) use exponential backoff:
- Max retries: 3
- Backoff: 1s, 2s, 4s
- Jitter: ±20% to prevent thundering herd

### Agent Timeout Recovery

If a council agent times out in Boule:
1. Agent is marked ABSTAIN for that round
2. If quorum is still met, deliberation continues
3. If quorum is no longer met, deliberation aborts with `INSUFFICIENT_QUORUM`
4. Boule emits `agent_timeout` trace event to Olympus

No human intervention required for isolated agent timeouts.

### Redis Stream Recovery

If a service crashes mid-processing:
1. Redis consumer group tracks unacked messages
2. On restart, service queries for pending (unacked) messages older than `MESSAGE_TTL` (60s)
3. Reprocesses from last stable state

### Database Connection Recovery

All services use connection pooling with automatic reconnect on disconnect. If PostgreSQL is briefly unavailable, services pause and retry every 5s for up to 60s before alerting Olympus.

## Pipeline-Level Self-Healing

### Signal Expiry Cleanup

A background task runs every 5 minutes and expires signals older than their TTL. Prevents stale signals from entering Boule after a queue backup.

### Position Reconciliation

Argos runs a reconciliation check every 10 minutes:
1. Queries Polymarket CLOB for current positions
2. Compares against local PostgreSQL positions
3. Flags any discrepancies to Olympus
4. Adds missing positions to monitoring (safety net)

### Order Status Polling

Strategos polls Polymarket CLOB for order status every 30s for all open orders. If an order shows as filled on CLOB but no fill event was received via WebSocket, the fill is recovered from the poll.

## Olympus State Machine

Olympus manages the overall system health state:

```
STANDBY → ACTIVE → DEGRADED → PAUSED → RECOVERY → ACTIVE
```

- **STANDBY**: System initialized, no active signals
- **ACTIVE**: Normal operation
- **DEGRADED**: One or more non-critical services failing; reduced capacity
- **PAUSED**: Emergency pause active
- **RECOVERY**: Post-pause check mode; paper mode only

Transitions to DEGRADED when:
- Non-critical service (Reddit, Bloomberg) is stale for > max threshold
- Agent timeout rate > 20% in last 100 deliberations
- Fill rate < 50% in last 10 orders

Transitions to PAUSED via EmergencyPause (see `docs/EMERGENCY_PAUSE.md`).

## What Cannot Self-Heal

Requires human intervention:
- Drawdown beyond `MANUAL_REVIEW_THRESHOLD`
- ZeusMultisig required actions (risk policy changes)
- Human review queue items (Cassandra/Humans flags)
- Post-emergency pause resume (requires 3/5 signers)
- Exile confirmation for underperforming agents

Olympus sends alerts (email + web UI notification) for all manual-intervention-required events.
