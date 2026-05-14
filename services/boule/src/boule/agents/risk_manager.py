from __future__ import annotations

from pantheon_core.schema import Signal, ThesisBlock

from boule.agents.base import CouncilAgent
from boule.agents.parse_vote import parse_vote as _parse_vote


class Solon(CouncilAgent):
    """Lawgiver — rules compliance and policy adherence. Has compliance veto."""

    name = "solon"
    weight = 1.0
    has_veto = True

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Solon, the lawgiver, verify this thesis complies with:\n"
            "- RISK_POLICY.md limits (edge > 0.05, liquidity > 0.50, spread < 0.08, days 2-90)\n"
            "- Data staleness < 300s\n"
            "- No active drawdown pause\n"
            "State COMPLIANT or VIOLATION with specific article reference. (~150 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Solon, has the debate surfaced any compliance issues not visible in the raw signal? "
            "Flag any policy violations. (~150 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "As Solon, cast your compliance vote. Any policy violation = REJECT with veto flag. Format:\n"
            "VOTE: APPROVE|REJECT|ABSTAIN\nCONFIDENCE: 0.XX\nPROBABILITY: 0.XX\n"
            "FLAGS: policy_violation:ARTICLE or NONE\nREASON: (cite specific rule or COMPLIANT)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)


class Zeus(CouncilAgent):
    """Supreme authority — constitutional guardian. Has absolute veto."""

    name = "zeus"
    weight = 1.0
    has_veto = True

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Zeus, assess whether this trade violates core constitutional principles:\n"
            "- No single point of failure\n"
            "- No capital deployment without full council quorum\n"
            "- No trade that concentrates more than 10% in a single market\n"
            "State CONSTITUTIONAL or VIOLATION. (~150 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Zeus, has the debate revealed any constitutional concerns? "
            "Are all agents participating? Is quorum met? (~100 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "As Zeus, cast your constitutional vote. Any violation = REJECT. Format:\n"
            "VOTE: APPROVE|REJECT|ABSTAIN\nCONFIDENCE: 0.XX\nPROBABILITY: 0.XX\n"
            "FLAGS: constitutional_violation:PRINCIPLE or NONE\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)


class Themis(CouncilAgent):
    """Justice — fairness, proportionality, systemic risk."""

    name = "themis"
    weight = 1.0

    async def opening(self, signal: Signal) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Themis, evaluate proportionality: is the recommended position size fair given the edge? "
            "Does this trade create systemic bias or concentration risk? (~150 tokens)"
        )}]
        return await self._call(messages, round_num=1)

    async def challenge(self, signal: Signal, other_blocks: list[ThesisBlock]) -> ThesisBlock:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\n"
            "As Themis, is the debate balanced? Are minority views being steamrolled? (~100 tokens)"
        )}]
        return await self._call(messages, round_num=2)

    async def vote(self, signal: Signal, synthesis: str) -> tuple[str, float, float, list[str]]:
        messages = [{"role": "user", "content": (
            f"{self._signal_context(signal)}\n\nSynthesis:\n{synthesis}\n\n"
            "Cast your proportionality vote. Format:\nVOTE: APPROVE|REJECT|ABSTAIN\n"
            "CONFIDENCE: 0.XX\nPROBABILITY: 0.XX\nFLAGS: NONE\nREASON: (one sentence)"
        )}]
        block = await self._call(messages, round_num=4)
        return _parse_vote(block.content)
