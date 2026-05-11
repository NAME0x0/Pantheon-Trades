# Olympus — Governance

Top-level system governance service.

## What It Does

1. Maintains system state machine (standby/active/degraded/paused/recovery)
2. Tracks and enforces goals board objectives
3. Runs adversarial mode security testing
4. Coordinates agent lifecycle: paper→live promotions, exile process
5. Propagates emergency pause to all services
6. Monitors for anomalies and alerts operators

## Setup

```bash
cd services/olympus
cp .env.example .env
uv run python -m olympus
```

## Structure

```
src/olympus/
  orchestrator.py       Main coordination logic
  state.py              System state machine
  goals_board.py        Goal tracking
  lifecycle.py          Agent lifecycle coordination
  exile.py              Agent exile process
  promotion.py          Paper-to-live promotion
  adversarial.py        Adversarial mode runner
  goals/
    daily_bread.py      Daily activity goal
    odyssey.py          Trade count milestone
    oracle_watch.py     Data freshness goal
    war_room.py         Drawdown goal
    forbidden_markets.py  Blacklist enforcement
```

## Tests

```bash
uv run pytest tests/ -v
```

## Docs

- `docs/OLYMPUS.md` — full service documentation
- `docs/GOALS_BOARD.md` — goal definitions
- `docs/ADVERSARIAL_MODE.md` — red-team testing
- `docs/EMERGENCY_PAUSE.md` — pause playbook
