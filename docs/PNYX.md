# Pnyx — Voting and Deliberation

The Pnyx (Πνύξ) was the hill in ancient Athens where the Ecclesia (citizen assembly) gathered to vote. In Pantheon Trades, the Pnyx represents the voting and consensus mechanics within the Boule deliberation system.

## Voting Mechanism

See `docs/BOULE.md` for the full debate protocol. This document covers the voting math.

## Vote Weights

Each agent has a base vote weight, modified by their credibility score from Ostrakon:

```python
effective_weight = base_weight * credibility_weight

# Where credibility_weight = max(0.25, min(2.5, ostrakon_credibility))
```

Base weights:
- Zeus: N/A (veto, not weighted vote)
- Solon: N/A (veto, not weighted vote)
- Hades: 2.0
- Athena: 1.5
- All others: 1.0
- Messengers: 0 (no vote)

## Weighted Approval Calculation

```python
total_weight_approve = sum(agent.effective_weight for agent in voted_approve)
total_weight_reject  = sum(agent.effective_weight for agent in voted_reject)
total_weight_all     = sum(agent.effective_weight for agent in all_voting_agents)

weighted_approval = total_weight_approve / (total_weight_approve + total_weight_reject)
```

Abstentions are excluded from the denominator — they neither approve nor reject.

Required: `weighted_approval >= 0.60`

## Quorum

Minimum quorum: 7 of 13 agents must cast a non-ABSTAIN vote.

If quorum is not met (e.g., too many timeouts), deliberation ends with `INSUFFICIENT_QUORUM` → ProofOfRestraint issued.

## Veto Hierarchy

```
Zeus veto       → immediate REJECTED (no vote proceeds)
Solon veto      → immediate REJECTED (no vote proceeds)
  └── unless Zeus explicitly overrides Solon (rare constitutional exception)
```

## Confidence Aggregation

Beyond the yes/no vote, Boule computes a council confidence score:

```python
council_probability = (
    sum(agent.probability_estimate * agent.effective_weight for agent in approved_agents) /
    sum(agent.effective_weight for agent in approved_agents)
)

council_confidence = (
    sum(agent.confidence * agent.effective_weight for agent in voting_agents) /
    sum(agent.effective_weight for agent in voting_agents)
)
```

`council_probability` is what gets passed to Areopagus as the trade probability.
`council_confidence` modulates position sizing (lower confidence → smaller Kelly fraction applied).

## Cassandra Protocol

If Cassandra raises a flag:
1. Flag is appended to the Thesis `cassandra_flags` list
2. Areopagus is notified to run secondary review even if council approves
3. Areopagus secondary review: Cassandra's specific concern is re-evaluated against data

Cassandra flag alone does not veto. It adds scrutiny. If Areopagus secondary review confirms the tail risk is unacceptable, the thesis is rejected at that stage.

## Vote Record

Every vote is part of the Trace and archived permanently. The on-chain `DecisionCourt.sol` records the vote summary hash for approved theses.
