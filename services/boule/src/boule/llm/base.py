"""Common LLM client surface used by every Boule council agent.

Each provider implementation returns a ``CompletionResult`` with the
plain text reply plus the total token count. The retry / circuit-breaker
plumbing is provider-agnostic and lives in ``boule.agents.base``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CompletionResult:
    text: str
    tokens: int


class LLMClient(Protocol):
    """Async LLM client interface.

    ``complete`` takes a system prompt + a list of role/content message
    dicts (Anthropic-style: ``[{"role": "user", "content": "..."}]``) and
    returns the assistant text + total token count. Implementations are
    expected to raise on transport / auth errors so the retry decorator
    upstream can react.
    """

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> CompletionResult: ...

    async def close(self) -> None: ...
