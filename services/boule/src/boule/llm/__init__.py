"""LLM provider adapters for Boule.

The council debate code is written against a single ``LLMClient`` protocol
so we can swap providers without touching the agent classes. Selection
happens at process boot via env:

    BOULE_LLM_PROVIDER = anthropic | gemini | openai | openrouter
                       | groq | together | deepseek | xai | ollama
                       | lm_studio | openai_compat   (default: anthropic)

The ``openai_compat`` selector is the escape hatch — it reads
``OPENAI_BASE_URL`` + ``OPENAI_API_KEY`` + ``OPENAI_MODEL`` so you can
point Boule at any OpenAI-compatible server (vLLM, LocalAI, TGI, a
custom proxy, etc.) without writing a new adapter.

If the chosen provider's key is missing or the call fails persistently,
we degrade rather than crash — the consumer logs and skips the signal.
"""

from __future__ import annotations

import os

from boule.llm.base import CompletionResult, LLMClient

__all__ = ["CompletionResult", "LLMClient", "build_default_client"]


def build_default_client() -> LLMClient:
    provider = os.environ.get("BOULE_LLM_PROVIDER", "anthropic").lower()

    # Pre-baked OpenAI-compat providers — all share one adapter.
    if provider in {
        "openai",
        "openrouter",
        "groq",
        "together",
        "deepseek",
        "xai",
        "grok",
        "ollama",
        "lm_studio",
        "lmstudio",
        "openai_compat",
    }:
        from boule.llm import openai_compat_client as oa

        if provider == "openai":
            return oa.openai(os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        if provider == "openrouter":
            return oa.openrouter(
                os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
            )
        if provider == "groq":
            return oa.groq(os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile"))
        if provider == "together":
            return oa.together(
                os.environ.get(
                    "TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"
                )
            )
        if provider == "deepseek":
            return oa.deepseek(os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"))
        if provider in {"xai", "grok"}:
            return oa.xai(os.environ.get("XAI_MODEL", "grok-2-latest"))
        if provider == "ollama":
            return oa.ollama(os.environ.get("OLLAMA_MODEL", "llama3.1"))
        if provider in {"lm_studio", "lmstudio"}:
            return oa.lm_studio(os.environ.get("LM_STUDIO_MODEL", "local-model"))
        # generic openai_compat — caller supplies OPENAI_BASE_URL + key + model
        return oa.OpenAICompatClient()

    if provider == "gemini":
        from boule.llm.gemini_client import GeminiClient

        return GeminiClient()
    if provider == "anthropic":
        from boule.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    raise ValueError(f"unknown BOULE_LLM_PROVIDER: {provider}")
