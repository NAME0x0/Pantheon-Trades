# Pantheon API

FastAPI gateway for the Pantheon Trades system.

## Stack

- Python 3.12, uv, FastAPI
- PostgreSQL (via SQLAlchemy + asyncpg)
- Redis (via aioredis)
- WebSocket streaming

## Setup

```bash
cd apps/api
cp .env.example .env
# Fill in env vars
uv run uvicorn pantheon_api.main:app --reload --port 8000
```

## Structure

```
src/pantheon_api/
  main.py          FastAPI app setup, middleware, CORS
  config.py        Settings (Pydantic BaseSettings)
  deps.py          FastAPI dependencies (auth, DB sessions)
  logging.py       Structured logging setup
  db.py            Database connection and session management
  routers/
    signals.py     GET /api/signals
    theses.py      GET /api/theses
    trades.py      GET /api/trades
    agents.py      GET /api/agents
    markets.py     GET /api/markets
    traces.py      GET /api/traces
    arc.py         GET /api/arc/proof, GET /api/arc/passport
    health.py      GET /health
  schemas/
    signal.py      Signal response schemas
    thesis.py      Thesis response schemas
    trade.py       Trade response schemas
    agent.py       Agent response schemas
    trace.py       Trace event schemas
  ws/
    stream.py      WebSocket handler + Redis bridge
```

## Authentication

SIWE + JWT. See `docs/AUTH.md`.

## Tests

```bash
cd apps/api
uv run pytest tests/ -v
```
