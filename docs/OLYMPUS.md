# Olympus — Governance

Mount Olympus was home to the twelve Olympian gods — the supreme governing authority of the Greek pantheon. In Pantheon Trades, Olympus is the top-level governance service that coordinates all other services, enforces goals, and manages the system's overall health.

## Responsibilities

1. Maintain system state machine (standby/active/degraded/paused/recovery)
2. Manage goals board — daily, weekly, and mission objectives
3. Run adversarial mode for security testing
4. Coordinate agent lifecycle: promotion from paper to live, exile process
5. Propagate emergency pause to all services
6. Monitor and alert on anomalies

## State Machine

```
STANDBY ──► ACTIVE ──► DEGRADED ──► PAUSED ──► RECOVERY ──► ACTIVE
                │                      ▲
                └──────────────────────┘ (emergency pause shortcut)
```

State transitions are driven by:
- Service health checks
- Drawdown thresholds
- Manual operator action
- ZeusMultisig

## Goals Board

`goals_board.py` tracks system-level objectives:

```python
class Goal(BaseModel):
    goal_id: str
    name: str
    description: str
    goal_type: Literal["daily", "weekly", "monthly", "mission"]
    target_metric: str
    target_value: float
    current_value: float
    status: Literal["on_track", "at_risk", "failed", "completed"]
    deadline: datetime
```

Example goals:
- **Daily Bread**: 1+ paper trades completed today
- **Odyssey**: 10+ live trades successfully closed
- **Oracle Watch**: data sources all fresh within last 30 min
- **War Room**: drawdown < 3% this week
- **Forbidden Markets**: zero trades on blacklisted market categories

`services/olympus/src/olympus/goals/` — each goal in its own module.

On-chain: `GoalsBoard.sol` records goal completions.

## Agent Lifecycle Management

### Promotion (Paper → Live)
```python
async def evaluate_for_promotion(strategy: Strategy):
    metrics = await ostrakon.get_strategy_metrics(strategy.id)
    if meets_promotion_criteria(metrics):
        await create_promotion_proposal(strategy)
        # Human operator review required
```

### Exile
```python
async def handle_exile_proposal(agent: Agent, reason: str):
    # Creates review item for human operators
    # After 48h or human confirmation:
    await moirai.atropos.terminate(agent, reason)
    await parthenon.passport.exile(agent.id, reason)
    await underworld.postmortem.start(agent)
```

## Adversarial Mode

`adversarial.py` — see `docs/ADVERSARIAL_MODE.md`.

## Service Files

`services/olympus/`:
- `orchestrator.py` — main coordination logic
- `state.py` — state machine
- `goals_board.py` — goal tracking
- `lifecycle.py` — agent lifecycle coordination
- `exile.py` — exile process
- `promotion.py` — paper-to-live promotion
- `adversarial.py` — adversarial mode runner
- `goals/` — individual goal implementations
  - `daily_bread.py` — daily activity goal
  - `odyssey.py` — trade count goal
  - `oracle_watch.py` — data freshness goal
  - `war_room.py` — drawdown goal
  - `forbidden_markets.py` — blacklist enforcement
