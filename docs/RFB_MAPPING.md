# RFB Mapping — Reason-For-Belief

RFB (Reason-For-Belief) maps each agent's vote to the specific evidence or reasoning that supports it. This creates a structured accountability chain: every vote is traceable to a specific claim, and every claim is traceable to specific data.

## Purpose

Without RFB mapping, agent votes are black boxes. With RFB:
1. Post-mortems can identify which specific beliefs were wrong
2. Hallucination detection can cross-check claims against data
3. Ostrakon can score not just the vote outcome but the reasoning quality
4. Humans reviewing traces can quickly understand *why* each agent voted as they did

## Structure

```python
class ReasonForBelief(BaseModel):
    agent: str
    vote: str                    # APPROVE / REJECT / ABSTAIN
    probability_estimate: float
    
    primary_belief: str          # The single most important belief supporting the vote
    supporting_evidence: list[str]  # Data points from signal context
    contradicting_evidence: list[str]  # Evidence that could counter this vote
    uncertainty_sources: list[str]  # What the agent is most uncertain about
    
    # Data citation: which signal fields does this belief rely on?
    data_citations: dict[str, str]   # {"belief_claim": "signal_field: value"}
```

## Example

Agent: Hades, Vote: REJECT, p=0.45

```json
{
  "primary_belief": "Resolution depends on regulatory decision with binary outcome uncertainty",
  "supporting_evidence": [
    "catalyst_score=0.92: SEC decision expected in 3 days",
    "Historical base rate for this market type: 38% resolution YES",
    "Sentiment score 0.31: mildly negative across news sources"
  ],
  "contradicting_evidence": [
    "Edge +0.14 suggests market may be underpricing YES",
    "Volume has increased 180% in last 24h (potential informed trading)"
  ],
  "uncertainty_sources": [
    "No prior information about the specific regulatory decision",
    "News sentiment is lagging; may not reflect latest developments"
  ],
  "data_citations": {
    "SEC decision expected in 3 days": "signal.catalyst_score=0.92, signal.resolution_date=T+3d",
    "Historical base rate 38%": "signal.category=crypto, signal.question_type=regulatory"
  }
}
```

## Integration with Traces

RFB data is part of each agent's `ThesisBlock` output. Parsed from the structured section of the agent's response (agents are prompted to include an `<rfb>` JSON section in their output).

## Integration with Underworld

Post-mortems extract `primary_belief` fields and cross-check them against resolution:
- Was the primary belief correct?
- Was the cited data accurate?
- Did the citing agent correctly interpret the data?

Results fed to `broken_assumptions.py` to build the catalog of recurring failures.

## Integration with Auditor

The Auditor agent receives all `data_citations` fields and verifies them against the shared signal context:
- Does the signal actually contain this value?
- Is the cited field's value accurately reported?
- Are there logical leaps between cited data and stated belief?

Audit failures logged to `underworld/hallucination_log.py`.
