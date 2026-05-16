"""OpenAI-compatible LLM adapter — one client, many providers.

The OpenAI `/v1/chat/completions` schema has become the de-facto lingua
franca for chat APIs. By pointing this adapter at a different base URL,
the same code path drives:

  - OpenAI                  api.openai.com/v1
  - OpenRouter              openrouter.ai/api/v1
  - Groq                    api.groq.com/openai/v1
  - Together AI             api.together.xyz/v1
  - Fireworks               api.fireworks.ai/inference/v1
  - DeepSeek                api.deepseek.com/v1
  - xAI Grok                api.x.ai/v1
  - LM Studio (local)       localhost:1234/v1
  - Ollama (local)          localhost:11434/v1   (Ollama's OpenAI-compat endpoint)
  - vLLM / TGI / LocalAI    any OpenAI-compat server you self-host

Selected at process boot via env:

    BOULE_LLM_PROVIDER=openai_compat
    OPENAI_BASE_URL=https://openrouter.ai/api/v1
    OPENAI_API_KEY=sk-or-v1-...
    OPENAI_MODEL=anthropic/claude-sonnet-4

The cache + spacing layers from gemini_client.py apply here too — same
identical-input → identical-output → free re-run guarantee.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from boule.llm.base import CompletionResult, LLMClient
from boule.llm.cache import cache_key, get as cache_get, put as cache_put

DEFAULT_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_API_KEY_ENV = os.environ.get("OPENAI_API_KEY_ENV", "OPENAI_API_KEY")
CALL_TIMEOUT_SECONDS = float(os.environ.get("OPENAI_TIMEOUT_SECONDS", "60"))
MAX_RETRIES = int(os.environ.get("OPENAI_MAX_RETRIES", "4"))

# Belt-and-suspenders parallelism / spacing — same knobs as the Gemini
# client so all providers honour the same throttle conventions.
MAX_PARALLEL = int(os.environ.get("OPENAI_CONCURRENCY", "4"))
MIN_SPACING_SECONDS = float(os.environ.get("OPENAI_MIN_SPACING_SECONDS", "0.0"))

_RETRYABLE = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


class OpenAITransientError(Exception):
    """Wrap 408 / 409 / 429 / 5xx so tenacity retries with backoff."""


class OpenAICompatClient(LLMClient):
    """Single client for every OpenAI-compatible provider."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        provider_label: str = "openai_compat",
    ) -> None:
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._model = model or DEFAULT_MODEL
        # Some local servers (LM Studio, Ollama, vLLM) don't enforce auth.
        # Pass an empty / placeholder key in that case.
        key = api_key
        if key is None:
            key = os.environ.get(DEFAULT_API_KEY_ENV) or os.environ.get("OPENAI_API_KEY", "")
        self._api_key = key
        self._provider_label = provider_label
        self._http = httpx.AsyncClient(
            timeout=CALL_TIMEOUT_SECONDS,
            headers={
                "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                "Content-Type": "application/json",
                # OpenRouter requires a referer + title for usage tracking.
                # Harmless for other providers.
                "HTTP-Referer": os.environ.get(
                    "OPENROUTER_HTTP_REFERER",
                    "https://github.com/NAME0x0/Pantheon-Trades",
                ),
                "X-Title": "Pantheon Trades",
            },
        )
        self._semaphore = asyncio.Semaphore(MAX_PARALLEL)
        self._spacing_lock = asyncio.Lock()
        self._last_call_t: float = 0.0

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
        # Cache lookup before any network.
        key = cache_key(
            provider=f"{self._provider_label}::{self._base_url}",
            model=self._model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        cached = cache_get(key)
        if cached is not None:
            return cached

        deterministic = os.environ.get("BOULE_LLM_DETERMINISTIC", "0") in ("1", "true", "True", "yes", "on")
        temperature = 0.0 if deterministic else float(os.environ.get("OPENAI_TEMPERATURE", "0.4"))
        top_p = 1.0 if deterministic else float(os.environ.get("OPENAI_TOP_P", "0.9"))

        body: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                *[
                    {"role": m["role"], "content": m["content"]}
                    for m in messages
                ],
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if deterministic:
            # OpenAI / OpenRouter / Groq / Together / DeepSeek all
            # accept `seed`. Providers that ignore it return identical
            # behaviour; providers that respect it pin sampling.
            body["seed"] = int(os.environ.get("BOULE_LLM_SEED", "42"))

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(MAX_RETRIES),
            wait=wait_exponential(multiplier=1.5, min=2, max=30),
            retry=retry_if_exception_type(_RETRYABLE + (OpenAITransientError,)),
            reraise=True,
        ):
            with attempt:
                async with self._semaphore:
                    await self._enforce_spacing()
                    resp = await asyncio.wait_for(
                        self._http.post(
                            f"{self._base_url}/chat/completions",
                            json=body,
                        ),
                        timeout=CALL_TIMEOUT_SECONDS,
                    )
                if resp.status_code in (408, 409, 429, 500, 502, 503, 504):
                    raise OpenAITransientError(
                        f"{self._provider_label} {resp.status_code}: {resp.text[:300]}"
                    )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"{self._provider_label} {resp.status_code}: {resp.text[:500]}"
                    )
                payload = resp.json()
                break

        text = _extract_text(payload)
        usage = payload.get("usage", {}) or {}
        tokens_in = int(usage.get("prompt_tokens", 0) or 0)
        tokens_out = int(usage.get("completion_tokens", 0) or 0)
        tokens = int(usage.get("total_tokens") or (tokens_in + tokens_out))
        # Use the provider's echoed model field as the fingerprint when
        # available so drift detection sees server-side rolls.
        fingerprint = f"{self._provider_label}/{payload.get('model') or self._model}"
        result = CompletionResult(
            text=text,
            tokens=tokens,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_fingerprint=fingerprint,
        )
        cache_put(key, result)
        return result

    async def _enforce_spacing(self) -> None:
        if MIN_SPACING_SECONDS <= 0:
            return
        async with self._spacing_lock:
            now = time.monotonic()
            elapsed = now - self._last_call_t
            if elapsed < MIN_SPACING_SECONDS:
                await asyncio.sleep(MIN_SPACING_SECONDS - elapsed)
            self._last_call_t = time.monotonic()

    async def close(self) -> None:
        await self._http.aclose()


def _extract_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0].get("message") or {})
    # Standard text reply.
    content = msg.get("content")
    if isinstance(content, str) and content:
        return content.strip()
    # Some providers (OpenAI multi-part) return a list of parts.
    if isinstance(content, list):
        chunks = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
        return "\n".join(chunks).strip()
    return ""


# ─── Pre-baked provider builders ──────────────────────────────────────
# Sugar so callers don't have to remember base URLs.

def openai(model: str = "gpt-4o-mini") -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url="https://api.openai.com/v1",
        api_key=os.environ.get("OPENAI_API_KEY"),
        model=model,
        provider_label="openai",
    )


def openrouter(model: str = "openai/gpt-4o-mini") -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        model=model,
        provider_label="openrouter",
    )


def groq(model: str = "llama-3.1-70b-versatile") -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
        model=model,
        provider_label="groq",
    )


def together(model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo") -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url="https://api.together.xyz/v1",
        api_key=os.environ.get("TOGETHER_API_KEY"),
        model=model,
        provider_label="together",
    )


def deepseek(model: str = "deepseek-chat") -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url="https://api.deepseek.com/v1",
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        model=model,
        provider_label="deepseek",
    )


def xai(model: str = "grok-2-latest") -> OpenAICompatClient:
    return OpenAICompatClient(
        base_url="https://api.x.ai/v1",
        api_key=os.environ.get("XAI_API_KEY"),
        model=model,
        provider_label="xai",
    )


def ollama(model: str = "llama3.1") -> OpenAICompatClient:
    """Local Ollama via its OpenAI-compatible endpoint."""
    return OpenAICompatClient(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="ollama",  # placeholder; Ollama ignores auth
        model=model,
        provider_label="ollama",
    )


def lm_studio(model: str = "local-model") -> OpenAICompatClient:
    """Local LM Studio server (OpenAI-compatible)."""
    return OpenAICompatClient(
        base_url=os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
        api_key="lm-studio",  # placeholder; LM Studio ignores auth
        model=model,
        provider_label="lm_studio",
    )
