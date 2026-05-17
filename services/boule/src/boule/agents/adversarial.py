"""Eris — the adversarial dissenter against emerging consensus.

Eris reads the round-2 transcript, infers the direction the council is
leaning, and argues the opposite case as forcefully as the evidence
allows. The intent is to restore dispersion that vanishes once a
deliberation cascades.

See ``services/boule/src/boule/prompts/eris.md`` for the prompt
contract that governs her behaviour at runtime.
"""

from __future__ import annotations

from collections import Counter

from pantheon_core.schema import Signal, ThesisBlock

from boule.agents.base import CouncilAgent
from boule.agents.parse_vote import parse_vote as _parse_vote


def _infer_lean(blocks: list[ThesisBlock]) -> str:
    """Sketch the emerging consensus from agent block content.

    We do not have structured vote signal at round 2 — agents are still
    arguing — so we look for the unambiguous tokens that appear in
    every prompt: APPROVE / REJECT / ABSTAIN, and the directional words
    YES / NO / BUY / SELL. Cheap but useful: if the round-2 transcript
    is leaning one way, Eris should argue the other.
    """
    if not blocks:
        return "unclear"
    counts: Counter[str] = Counter()
    for b in blocks:
        upper = b.content.upper()
        for token, lean in (
            ("APPROVE", "yes"),
            ("BUY", "yes"),
            ("LONG", "yes"),
            ("REJECT", "no"),
            ("SELL", "no"),
            ("SHORT", "no"),
        ):
            if token in upper:
                counts[lean] += 1
    if not counts:
        return "unclear"
    top, _ = counts.most_common(1)[0]
    return top


class Eris(CouncilAgent):
    """Devil's advocate; attacks the emerging consensus."""

    name = "eris"
    weight = 0.8  # softer than synthesis voices — dissent is signal, not vote

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Eris, this is round 1. The council has not spoken yet. "
            "Sketch the strongest argument for whichever side seems "
            "least obvious to you — pre-empt the consensus you "
            "anticipate forming. (~200 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        # Pull the round-1 blocks so we can read the lean.
        round_one = [b for b in other_blocks if b.round == 1 and b.agent != self.name]
        lean = _infer_lean(round_one)
        target = "NO / REJECT" if lean == "yes" else "YES / APPROVE"
        if lean == "unclear":
            target = "whichever side is currently overrepresented"
        snippet = "\n\n".join(
            f"[{b.agent} R{b.round}]: {b.content[:280]}" for b in round_one[:6]
        )
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            f"Round-1 transcript (summary):\n{snippet}\n\n"
            f"Consensus appears to lean: **{lean.upper()}**. "
            f"As Eris, build the strongest credible case for **{target}**. "
            "Cite specific evidence from the signal context. "
            "If you genuinely cannot construct a credible counter-case, "
            "say so explicitly — that is also a valuable signal. "
            "(~250 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "As Eris, cast a vote. Your vote should reflect the strength "
            "of the dissenting case you built — if it is strong, vote "
            "against the consensus. If you could not find a credible "
            "counter, vote ABSTAIN and explain why. Format:\n"
            "VOTE: APPROVE|REJECT|ABSTAIN\nCONFIDENCE: 0.XX\n"
            "PROBABILITY: 0.XX\nFLAGS: (comma-separated or NONE)\n"
            "REASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)
