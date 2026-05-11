# Areopagus — Risk Court

The Areopagus (Ἄρειος Πάγος, "Hill of Ares") was Athens' most prestigious court — a council of elders with authority to overrule dangerous decisions. In Pantheon Trades, Areopagus is the risk gating service that reviews every council-approved thesis before execution.

## Role

Areopagus sits between Boule and Strategos. It applies hard quantitative risk limits that the LLM council cannot override. Even a unanimous council vote can be blocked by Areopagus if the risk policy is violated.

## Gates

### Gate 1: Quorum and Veto Check
First: verifies Boule vote summary. Rejects if:
- Zeus veto was cast
- Solon veto was cast
- Quorum was not met

### Gate 2: Data Freshness
Rejects if `signal.staleness_seconds > 300` or `signal.source_trust_score < 0.5`.

### Gate 3: Market Liquidity
Rejects if `signal.liquidity_score < MIN_LIQUIDITY_SCORE` (default: 0.50).
Rejects if `signal.spread > MAX_SPREAD` (default: 0.08).

### Gate 4: Drawdown Check
Rejects if any active drawdown pause is in effect (see `docs/RISK_POLICY.md`).

### Gate 5: Portfolio Exposure
Rejects if adding this position would exceed:
- Max total exposure (40% default)
- Max category exposure (15% default)
- Max correlated exposure (10% default)

### Gate 6: Kelly Sizing
Computes half-Kelly position size:
```python
full_kelly = edge / (1 - market_probability + edge)
half_kelly = full_kelly * 0.5
final_size_pct = min(half_kelly, MAX_POSITION_PCT)  # cap at 5%
```

If `final_size_pct < MIN_POSITION_THRESHOLD` (0.5%), rejects as sub-threshold.

### Gate 7: Invalidation Check
Verifies the thesis exit conditions are not already triggered at current prices. If the current market probability has already moved past `exit_conditions.stop`, rejects (stale thesis).

### Gate 8: Cassandra Secondary Review
If any Cassandra flag exists, Areopagus runs a secondary check:
- Looks up the specific flag concern in Pythia data
- If the flagged risk is confirmed by data, rejects
- If not confirmed, approves with Cassandra flag noted

## Outputs

### Approved
```python
ApprovalToken(
    token_id=uuid4(),
    thesis_id=thesis.thesis_id,
    final_size_pct=final_size_pct,
    final_size_usdc=portfolio_value * final_size_pct,
    direction=thesis.direction,
    expires_at=now() + timedelta(minutes=15),
    gates_passed=[1,2,3,4,5,6,7,8],
    notes=""
)
```

### Rejected
```python
RejectionRecord(
    rejection_id=uuid4(),
    thesis_id=thesis.thesis_id,
    reason="DRAWDOWN_PAUSE",
    details="Active 24h pause from 3.1% daily drawdown at 14:22 UTC",
    gates_failed=[4],
    timestamp=now()
)
```
ProofOfRestraint issued for all rejections.

### Resized
Same as Approved but with a note explaining the resize (e.g., "Kelly cap applied: 6.2% → 5.0%").

## Policy

All limits live in `docs/RISK_POLICY.md`. Areopagus reads policy from config at startup and reloads on SIGHUP.

Changes require ZeusMultisig approval. See `docs/ZEUS_MULTISIG.md`.

## Service

`services/areopagus/`:
- `gates.py` — main gate evaluation logic
- `kelly.py` — Kelly criterion calculator
- `drawdown.py` — drawdown tracker
- `sizing.py` — position sizing
- `invalidation.py` — invalidation checks
- `policy.py` — policy config loader
