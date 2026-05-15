"""LLM provider adapters for Boule.

The council debate code is written against a single ``LLMClient`` protocol
so we can swap providers (Anthropic, Gemini, local) without touching the
agent classes. Selection happens at process boot via env:

    BOULE_LLM_PROVIDER = anthropic | gemini   (default: anthropic)

If the chosen provider's key is missing or the call fails persistently,
we degrade rather than crash — the consumer logs and skips the signal.
"""

from __future__ import annotations

import os

from boule.llm.base import CompletionResult, LLMClient

__all__ = ["CompletionResult", "LLMClient", "build_default_client"]


def build_default_client() -> LLMClient:
    provider = os.environ.get("BOULE_LLM_PROVIDER", "anthropic").lower()
    if provider == "gemini":
        from boule.llm.gemini_client import GeminiClient

        return GeminiClient()
    if provider == "anthropic":
        from boule.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    raise ValueError(f"unknown BOULE_LLM_PROVIDER: {provider}")
