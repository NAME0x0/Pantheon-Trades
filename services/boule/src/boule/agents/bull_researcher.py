"""Bull/risk axis of the council: Ares (advocate) and Hades (risk sovereign)."""

from __future__ import annotations

from pantheon_core.schema import Signal, ThesisBlock

from boule.agents.base import CouncilAgent
from boule.agents.parse_vote import parse_vote as _parse_vote  # re-exported

__all__ = ["Ares", "HadesAgent", "_parse_vote"]


class Ares(CouncilAgent):
    """Bull advocate — argues the aggressive upside case."""

    name = "ares"
    weight = 1.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [
            {
                "role": "user",
                "content": (
                    f"{self._signal_context(signal)}\n\n"
                    "As Ares, the bull advocate, provide your opening assessment. "
                    "Argue the strongest possible case for the direction implied by the positive edge. "
                    "Identify momentum, catalysts, and confirming signals. Cite the data provided. "
                    "Be concrete: specify what would change your mind. (~200 tokens)"
                ),
            }
        ]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        bear_blocks = [b for b in other_blocks if b.agent in ("hades", "cassandra") and b.round == 1]
        challenges = "\n\n".join(
            f"[{b.agent} Round {b.round}]: {b.content[:500]}" for b in bear_blocks[:3]
        )
        if not challenges:
            challenges = "(no bear/risk positions surfaced yet)"
        messages = [
            {
                "role": "user",
                "content": (
                    f"{self._signal_context(signal)}\n\n"
                    f"Bear/risk positions to challenge:\n{challenges}\n\n"
                    "As Ares, rebut the strongest bear arguments. Concede explicitly where they are correct, "
                    "and explain why the remaining bull case still dominates. (~200 tokens)"
                ),
            }
        ]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [
            {
                "role": "user",
                "content": (
                    f"{self._signal_context(signal)}\n\n"
                    f"Council synthesis:\n{synthesis}\n\n"
                    "Cast your final vote. Respond in EXACTLY this format with no extra prose:\n"
                    "VOTE: APPROVE|REJECT|ABSTAIN\n"
                    "CONFIDENCE: 0.XX\n"
                    "PROBABILITY: 0.XX\n"
                    "FLAGS: comma_separated_or_NONE\n"
                    "REASON: one sentence"
                ),
            }
        ]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)


class HadesAgent(CouncilAgent):
    """Risk sovereign — maximum-loss scenarios. Weight 2x on risk dimensions."""

    name = "hades"
    weight = 2.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [
            {
                "role": "user",
                "content": (
                    f"{self._signal_context(signal)}\n\n"
                    "As Hades, the risk sovereign, identify the maximum plausible loss scenario. "
                    "What black swans apply? What is the market pricing in that this signal misses? "
                    "Be quantitative about tail probabilities. (~200 tokens)"
                ),
            }
        ]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        bull_blocks = [b for b in other_blocks if b.agent == "ares" and b.round == 1]
        challenges = "\n\n".join(f"[{b.agent}]: {b.content[:500]}" for b in bull_blocks[:2])
        if not challenges:
            challenges = "(no bull position surfaced yet)"
        messages = [
            {
                "role": "user",
                "content": (
                    f"{self._signal_context(signal)}\n\n"
                    f"Bull arguments to stress-test:\n{challenges}\n\n"
                    "As Hades, identify what the bull case is ignoring. "
                    "What tail risk causes maximum loss for the proposed position? (~200 tokens)"
                ),
            }
        ]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [
            {
                "role": "user",
                "content": (
                    f"{self._signal_context(signal)}\n\n"
                    f"Council synthesis:\n{synthesis}\n\n"
                    "Cast your final vote from a risk perspective. Format:\n"
                    "VOTE: APPROVE|REJECT|ABSTAIN\n"
                    "CONFIDENCE: 0.XX\n"
                    "PROBABILITY: 0.XX\n"
                    "FLAGS: comma_separated_or_NONE\n"
                    "REASON: one sentence"
                ),
            }
        ]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)
