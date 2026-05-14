from __future__ import annotations

from pantheon_core.schema import Signal, ThesisBlock

from boule.agents.base import CouncilAgent
from boule.agents.parse_vote import parse_vote as _parse_vote


class Hephaestus(CouncilAgent):
    """Execution mechanic — feasibility, slippage, fill probability."""

    name = "hephaestus"
    weight = 1.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Hephaestus, evaluate execution feasibility:\n"
            f"- Spread: {signal.spread:.2%} (limit 8%)\n"
            f"- Volume 24h: ${signal.volume_24h:,.0f} USDC\n"
            f"- Liquidity score: {signal.liquidity_score:.3f}\n"
            "Estimate fill probability, expected slippage, and optimal order type. "
            "Flag if execution is not feasible. (~150 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Hephaestus, has the proposed position size changed from the debate? "
            "Re-evaluate execution feasibility for the size under discussion. (~100 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "As Hephaestus, cast your execution feasibility vote. "
            "REJECT if fill probability < 70% or slippage would eliminate edge. Format:\n"
            "VOTE: APPROVE|REJECT|ABSTAIN\nCONFIDENCE: 0.XX\nPROBABILITY: 0.XX\n"
            "FLAGS: execution_risk:REASON or NONE\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        vote, conf, prob, flags = _parse_vote(block.content)
        return vote, conf, prob, flags


class Daedalus(CouncilAgent):
    """Structural analyst — complexity and hidden dependencies."""

    name = "daedalus"
    weight = 1.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Daedalus, analyze structural risk: Is the strategy too complex? "
            "Are there hidden dependencies? What second-order effects could emerge? (~150 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Daedalus, identify the structural vulnerabilities the debate has not addressed. (~100 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "Cast your structural vote. Format:\nVOTE: APPROVE|REJECT|ABSTAIN\n"
            "CONFIDENCE: 0.XX\nPROBABILITY: 0.XX\nFLAGS: structural_risk:REASON or NONE\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)


class HumansAgent(CouncilAgent):
    """Human oversight representation."""

    name = "humans"
    weight = 1.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Humans (human oversight representative): Would a reasonable, experienced trader approve this? "
            "Flag if this needs human review. (~150 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Humans, flag any points where human judgment should override the AI consensus. (~100 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "Cast your human oversight vote. Format:\nVOTE: APPROVE|REJECT|ABSTAIN\n"
            "CONFIDENCE: 0.XX\nPROBABILITY: 0.XX\nFLAGS: human_review_required or NONE\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)
