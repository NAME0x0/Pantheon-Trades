"""Gemini provider adapter using the Generative Language v1beta REST API.

Picks ``gemini-2.5-flash`` by default — fast, free-tier-friendly, and
already validated against the Pantheon prompts in the bench harness. To
override pass ``BOULE_GEMINI_MODEL=gemini-2.5-pro`` (or similar) at boot.

Anthropic-style message dicts ([{"role": "user", "content": "..."}])
are translated into Gemini's parts format before submission so the
council agent classes do not need provider-specific code paths.
"""

from __future__ import annotations

import asyncio
import os

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from boule.llm.base import CompletionResult, LLMClient


DEFAULT_MODEL = os.environ.get("BOULE_GEMINI_MODEL", "gemini-2.5-flash")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
CALL_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 5

# Free-tier Gemini rate-limits at ~10 RPM. With 10 council agents fanning out
# in parallel we trivially blow that. Throttle to N concurrent calls.
MAX_PARALLEL = int(os.environ.get("BOULE_GEMINI_CONCURRENCY", "1"))

_RETRYABLE = (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)


class GeminiTransientError(Exception):
    """Wrap 429 / 5xx responses so tenacity retries with backoff."""


class GeminiClient(LLMClient):
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self._model = model
        self._api_key = os.environ["GEMINI_API_KEY"]
        self._http = httpx.AsyncClient(timeout=CALL_TIMEOUT_SECONDS)
        self._semaphore = asyncio.Semaphore(MAX_PARALLEL)

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
        body = {
            "contents": [
                {
                    "role": "user" if m["role"] == "user" else "model",
                    "parts": [{"text": m["content"]}],
                }
                for m in messages
            ],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {
                # Gemini counts "thinking" tokens against the output budget,
                # so give the council enough room to actually produce a
                # vote block in addition to the model's silent reasoning.
                "maxOutputTokens": max(max_tokens, 1024) + 1024,
                "temperature": 0.4,
                "topP": 0.9,
            },
        }

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(MAX_RETRIES),
            wait=wait_exponential(multiplier=2, min=4, max=60),
            retry=retry_if_exception_type(_RETRYABLE + (GeminiTransientError,)),
            reraise=True,
        ):
            with attempt:
                async with self._semaphore:
                    resp = await asyncio.wait_for(
                        self._http.post(
                            f"{BASE_URL}/models/{self._model}:generateContent",
                            params={"key": self._api_key},
                            json=body,
                        ),
                        timeout=CALL_TIMEOUT_SECONDS,
                    )
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise GeminiTransientError(f"gemini {resp.status_code}: {resp.text[:200]}")
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"gemini {resp.status_code}: {resp.text[:500]}"
                    )
                payload = resp.json()
                break

        text = _extract_text(payload)
        usage = payload.get("usageMetadata", {})
        tokens = int(usage.get("totalTokenCount", 0) or 0)
        return CompletionResult(text=text, tokens=tokens)

    async def close(self) -> None:
        await self._http.aclose()


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    chunks: list[str] = []
    for part in parts:
        text = part.get("text")
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()
