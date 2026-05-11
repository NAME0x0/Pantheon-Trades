# Hermes — Event Routing

Hermes (Ἑρμῆς) was the messenger god — patron of communication, commerce, and boundaries. In Pantheon Trades, Hermes refers to the event routing and messaging layer that connects all services.

## Infrastructure

Hermes is not a standalone service — it's the messaging infrastructure built on Redis Streams.

## Redis Stream Architecture

```
apollo:signals       → consumed by: Boule (market_scanner)
boule:theses         → consumed by: Areopagus
areopagus:approvals  → consumed by: Strategos
areopagus:rejections → consumed by: Parthenon (ProofOfRestraint)
strategos:trades     → consumed by: Argos, Parthenon, Ostrakon
strategos:exits      → consumed by: Argos
argos:pnl            → consumed by: web UI (WebSocket), PostgreSQL
argos:exits          → consumed by: Parthenon, Ostrakon
ostrakon:scores      → consumed by: Boule (memory), web UI
ostrakon:proposals   → consumed by: Olympus
parthenon:manifests  → consumed by: PostgreSQL
olympus:state        → broadcast to: all services
olympus:pause        → broadcast to: all services (emergency)
boule:traces         → consumed by: Parthenon, web UI (WebSocket)
boule:invalidation   → consumed by: Argos
```

## Consumer Groups

Each stream uses Redis consumer groups for exactly-once delivery:

```python
# Boule consumes signals with consumer group
redis.xreadgroup(
    groupname="boule-workers",
    consumername="boule-1",
    streams={"apollo:signals": ">"},
    count=1,
    block=0
)
```

Unacked messages are requeued by a watchdog after `MESSAGE_TTL` (default: 60s).

## Hermes Gate

See `docs/HERMES_GATE.md` for the API gateway routing layer.

## Event Schema

All events use a common envelope:

```python
class Event(BaseModel):
    event_id: str       # uuid4
    event_type: str     # e.g., "signal.created"
    source: str         # producing service name
    payload: dict       # event-specific data
    timestamp: datetime
    correlation_id: str # trace ID for correlating events across services
```

## WebSocket Bridge

The API gateway (`apps/api/ws/stream.py`) bridges Redis streams to the web UI via WebSocket:

- `/ws/signals` — live signal events
- `/ws/traces` — live trace events during deliberations
- `/ws/pnl` — live PnL updates
- `/ws/leaderboard` — score updates

The bridge subscribes to relevant Redis streams and forwards filtered events to connected WebSocket clients.

## Dead Letter Queue

Failed messages (3 retries exhausted) are sent to `hermes:dlq`. Olympus monitors this queue and alerts on accumulation.
