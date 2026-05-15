"""Anthropic Claude provider adapter."""

from __future__ import annotations

import asyncio
import os

import anthropic
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from boule.llm.base import CompletionResult, LLMClient
from boule.llm.cache import cache_key, get as cache_get, put as cache_put


DEFAULT_MODEL = os.environ.get("BOULE_ANTHROPIC_MODEL", "claude-sonnet-4-6")
CALL_TIMEOUT_SECONDS = 45.0
MAX_RETRIES = 3

_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class AnthropicClient(LLMClient):
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> CompletionResult:
        # Cache lookup before any network. Identical inputs return the
        # prior result and never bill the provider.
        key = cache_key(
            provider="anthropic",
            model=self._model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        cached = cache_get(key)
        if cached is not None:
            return cached

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(MAX_RETRIES),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=True,
        ):
            with attempt:
                response = await asyncio.wait_for(
                    self._client.messages.create(
                        model=self._model,
                        max_tokens=max_tokens,
                        system=system,
                        messages=messages,
                    ),
                    timeout=CALL_TIMEOUT_SECONDS,
                )
                break
        text = _extract_text(response)
        usage = getattr(response, "usage", None)
        tokens = 0
        if usage is not None:
            tokens = (getattr(usage, "input_tokens", 0) or 0) + (
                getattr(usage, "output_tokens", 0) or 0
            )
        result = CompletionResult(text=text, tokens=tokens)
        cache_put(key, result)
        return result

    async def close(self) -> None:
        await self._client.close()


def _extract_text(response) -> str:
    chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            chunks.append(getattr(block, "text", "") or "")
        elif block_type is None and hasattr(block, "text"):
            chunks.append(block.text or "")
    return "\n".join(chunks).strip()
