# Hermes Gate — API Gateway

The Hermes Gate is the API gateway — the boundary between the internal services and the outside world (web UI, external callers, webhook receivers).

## Implementation

`apps/api/` — FastAPI application serving as the gateway.

All external HTTP and WebSocket traffic enters through this gateway. Internal services communicate via Redis Streams directly and do not expose HTTP endpoints to external callers.

## Routes

### Signals
- `GET /api/signals` — list recent signals, filterable by band, market, timeframe
- `GET /api/signals/{signal_id}` — get specific signal

### Theses
- `GET /api/theses` — list theses, filterable by status, market, date
- `GET /api/theses/{thesis_id}` — get full thesis with agent votes

### Trades
- `GET /api/trades` — list executed trades
- `GET /api/trades/{trade_id}` — get trade detail with PnL

### Agents
- `GET /api/agents` — list agents with current scores
- `GET /api/agents/{agent_name}` — agent detail, history, leaderboard position

### Traces
- `GET /api/traces` — list deliberation traces
- `GET /api/traces/{trace_id}` — full trace with per-agent per-round events

### ARC / On-Chain
- `GET /api/arc/proof/{thesis_id}` — get on-chain proof for a thesis
- `GET /api/arc/passport/{agent_name}` — get agent passport from Arc Testnet

### Webhooks
- `POST /api/webhooks/polymarket` — Polymarket resolution webhooks (HMAC-verified)

### WebSockets
- `WS /ws/signals` — live signal stream
- `WS /ws/traces` — live deliberation trace stream
- `WS /ws/pnl` — live PnL stream

## Authentication

All endpoints (except health check) require authentication.

SIWE (Sign-In With Ethereum) for wallet-based auth. See `docs/SIWE.md`.
JWT tokens issued after SIWE verification. See `docs/AUTH.md`.

## RBAC

Role-based access. See `docs/RBAC.md`.

| Role | Access |
|------|--------|
| `viewer` | Read-only: signals, theses, traces, leaderboard |
| `operator` | viewer + manual override, settings |
| `admin` | operator + ZeusMultisig actions |

## Rate Limiting

- Public endpoints: 60 req/min per IP
- Authenticated endpoints: 300 req/min per user
- WebSocket connections: max 5 simultaneous per user

## Webhook Security

Polymarket webhooks verified via HMAC-SHA256 signature header. Signature secret stored in `POLYMARKET_WEBHOOK_SECRET` env var.

## Health Check

`GET /health` — returns 200 with service status. No auth required.

```json
{
  "status": "ok",
  "services": {
    "redis": "ok",
    "postgres": "ok",
    "pythia": "ok",
    "apollo": "degraded",
    "boule": "ok"
  }
}
```
