# Ostrakon — Agent Scoring

See `docs/SCORING.md` for full scoring methodology.

## Overview

Ostrakon (ὄστρακον) is the service that scores all council agents after every market resolution. Its outputs feed back into Boule (credibility weights) and Olympus (exile proposals).

## Service Files

`services/ostrakon/`:
- `metrics.py` — metric aggregation pipeline
- `brier.py` — Brier score computation
- `calibration.py` — calibration curve analysis
- `sharpe.py` — Sharpe ratio computation
- `leaderboard.py` — leaderboard construction and publishing
- `rewards.py` — reward allocation and ERC-8004 reputation updates

## Resolution Event Handling

On market resolution:

```python
async def handle_resolution(market_id: str, outcome: float):
    theses = await db.get_theses_for_market(market_id, status="executed")
    for thesis in theses:
        for agent_vote in thesis.agents:
            brier = (agent_vote.probability_estimate - outcome) ** 2
            await update_agent_score(
                agent_name=agent_vote.agent,
                thesis_id=thesis.thesis_id,
                brier_delta=brier,
                direction=thesis.direction,
                outcome=outcome
            )
    await rebuild_leaderboard()
    await publish_credibility_weights()
```

## Credibility Weight Update

After each rebuild, updated weights published to `ostrakon:weights` Redis stream. Boule consumes this on each new deliberation.

## On-Chain

`AgentReputation.sol` updated after each resolution:
- Raw Brier delta recorded per agent per thesis
- Cumulative reputation score updated
- Events emitted for public audit

Calls made by `rewards.py` via `parthenon/erc8004_client.py`.
