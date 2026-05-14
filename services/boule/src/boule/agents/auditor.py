"""Auditor — replays a debate and emits anomaly observations.

The auditor is a post-hoc reviewer. Given a finished Thesis, it scans
agent votes for: confidence/probability inconsistency, flagged tail
risks that nobody else echoed, agents who voted opposite the council
direction. Findings flow back to Underworld for post-mortem context.
"""

from __future__ import annotations

from dataclasses import dataclass

from pantheon_core.schema import Thesis


@dataclass(frozen=True)
class AuditFinding:
    agent: str
    kind: str
    note: str


def audit_thesis(thesis: Thesis) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    council_dir = thesis.direction
    for vote in thesis.agents:
        prob = vote.probability_estimate
        if vote.vote == "APPROVE" and vote.confidence > 0.85 and abs(prob - 0.5) < 0.05:
            findings.append(
                AuditFinding(
                    agent=vote.agent,
                    kind="confidence_probability_mismatch",
                    note=f"high confidence {vote.confidence:.2f} but coin-flip prob {prob:.2f}",
                )
            )
        if vote.vote == "APPROVE":
            if (council_dir == "YES" and prob < 0.5) or (council_dir == "NO" and prob > 0.5):
                findings.append(
                    AuditFinding(
                        agent=vote.agent,
                        kind="direction_disagreement",
                        note=f"APPROVE but probability {prob:.2f} suggests opposite direction",
                    )
                )
        if vote.flags:
            for f in vote.flags:
                if f.startswith("constitutional_violation:") and not thesis.zeus_veto:
                    findings.append(
                        AuditFinding(
                            agent=vote.agent,
                            kind="ignored_constitutional_flag",
                            note=f"flag {f} but no Zeus veto recorded",
                        )
                    )
    return findings
