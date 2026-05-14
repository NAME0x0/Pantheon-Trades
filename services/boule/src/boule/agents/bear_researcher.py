from __future__ import annotations

from pantheon_core.schema import Signal, ThesisBlock

from boule.agents.base import CouncilAgent
from boule.agents.parse_vote import parse_vote as _parse_vote


class Athena(CouncilAgent):
    """Strategic wisdom — logical consistency and synthesis."""

    name = "athena"
    weight = 1.5

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Athena, evaluate the logical consistency of this trade hypothesis. "
            "Are the assumptions internally coherent? Is the edge calculation sound? "
            "What is the quality of the underlying reasoning? (~200 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        all_text = "\n\n".join(f"[{b.agent} R{b.round}]: {b.content[:300]}" for b in other_blocks[:4])
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            f"Other agents' positions:\n{all_text}\n\n"
            "As Athena, identify the logical flaws or strengths across the debate. "
            "Which arguments are most compelling and why? (~200 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def synthesize(self, signal: Signal, all_blocks: list[ThesisBlock]) -> ThesisBlock:
        """Round 3 — Athena synthesizes the full debate."""
        debate_text = "\n\n".join(
            f"[{b.agent} Round {b.round}]: {b.content[:400]}" for b in all_blocks
        )
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            f"Full debate transcript:\n{debate_text}\n\n"
            "As Athena, synthesize the debate. Summarize: the bull case, the bear case, "
            "key contested points, and your net assessment of the probability and edge quality. "
            "This synthesis will inform all agents' final votes. (~300 tokens)"
        )}]
        return await self._call(messages, round_num=3)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "Cast your final vote. Format:\nVOTE: APPROVE|REJECT|ABSTAIN\n"
            "CONFIDENCE: 0.XX\nPROBABILITY: 0.XX\nFLAGS: NONE\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)


class Cassandra(CouncilAgent):
    """Prophetic warning — tail risks and ignored warnings."""

    name = "cassandra"
    weight = 1.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Cassandra, identify low-probability catastrophic outcomes. "
            "What is the market missing? What tail risks are being ignored? "
            "What scenario would cause maximum regret? (~200 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Cassandra, what warnings are being dismissed or underweighted by the other agents? "
            "Focus on second-order effects and hidden risks. (~200 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "Cast your vote. Any unresolved tail risk must be listed in FLAGS. Format:\n"
            "VOTE: APPROVE|REJECT|ABSTAIN\nCONFIDENCE: 0.XX\nPROBABILITY: 0.XX\n"
            "FLAGS: (comma-separated tail risks or NONE)\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        vote, conf, prob, flags = _parse_vote(block.content)
        return vote, conf, prob, flags
