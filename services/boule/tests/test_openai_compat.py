"""Tests for the universal OpenAI-compatible adapter.

We do not hit the network — the test patches ``httpx.AsyncClient.post``
so the same code path covers every provider that speaks the OpenAI
chat/completions schema (OpenAI, OpenRouter, Groq, Together, DeepSeek,
xAI, Ollama, LM Studio, vLLM, etc.).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from boule.llm.base import CompletionResult
from boule.llm.openai_compat_client import (
    OpenAICompatClient,
    OpenAITransientError,
    _extract_text,
    deepseek,
    groq,
    lm_studio,
    ollama,
    openai,
    openrouter,
    together,
    xai,
)


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOULE_LLM_CACHE_DIR", str(tmp_path / "boule-llm"))
    monkeypatch.setenv("BOULE_LLM_CACHE", "1")
    yield


def _fake_response(payload: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        request=httpx.Request("POST", "http://test"),
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
    )


def _ok_payload(text: str = "APPROVE p=0.62 c=0.85", total_tokens: int = 240) -> dict:
    return {
        "id": "cmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 120, "total_tokens": total_tokens},
    }


def test_extract_text_string_content():
    assert _extract_text(_ok_payload("hello")) == "hello"


def test_extract_text_list_parts():
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {"type": "text", "text": "a"},
                        {"type": "text", "text": "b"},
                    ]
                }
            }
        ]
    }
    assert _extract_text(payload) == "a\nb"


def test_extract_text_empty():
    assert _extract_text({}) == ""
    assert _extract_text({"choices": []}) == ""


def test_complete_returns_cached_when_present(monkeypatch):
    """Cache hit must short-circuit the network call entirely."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    client = OpenAICompatClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o-mini",
    )

    # Seed the cache by writing the same result the adapter would.
    from boule.llm.cache import cache_key, put

    key = cache_key(
        provider="openai_compat::https://api.openai.com/v1",
        model="gpt-4o-mini",
        system="be terse",
        messages=[{"role": "user", "content": "vote?"}],
        max_tokens=256,
    )
    put(key, CompletionResult(text="cached!", tokens=42))

    called = {"n": 0}

    async def boom(*_a, **_kw):  # pragma: no cover — must not be called
        called["n"] += 1
        raise RuntimeError("network must not be hit on cache hit")

    monkeypatch.setattr(httpx.AsyncClient, "post", boom)

    async def run():
        r = await client.complete(
            system="be terse",
            messages=[{"role": "user", "content": "vote?"}],
            max_tokens=256,
        )
        await client.close()
        return r

    out = asyncio.run(run())
    assert out.text == "cached!"
    assert out.tokens == 42
    assert called["n"] == 0


def test_complete_writes_to_cache_on_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    client = OpenAICompatClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o-mini",
    )

    async def fake_post(self, *_a, **_kw):
        return _fake_response(_ok_payload("APPROVE", 100))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    async def run():
        first = await client.complete(
            system="s", messages=[{"role": "user", "content": "q"}], max_tokens=128,
        )
        # Second call should be served entirely from disk cache.
        second = await client.complete(
            system="s", messages=[{"role": "user", "content": "q"}], max_tokens=128,
        )
        await client.close()
        return first, second

    first, second = asyncio.run(run())
    assert first.text == "APPROVE"
    assert second.text == "APPROVE"
    assert first.tokens == second.tokens


def test_429_raises_transient_for_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    client = OpenAICompatClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o-mini",
    )

    async def fake_post(self, *_a, **_kw):
        return httpx.Response(
            status_code=429,
            request=httpx.Request("POST", "http://test"),
            content=b'{"error":{"message":"rate limited"}}',
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    async def run():
        await client.complete(
            system="s", messages=[{"role": "user", "content": "q"}], max_tokens=8,
        )

    with pytest.raises((OpenAITransientError, RuntimeError)):
        asyncio.run(run())


def test_provider_builders_wire_correct_base_urls(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-1")
    monkeypatch.setenv("GROQ_API_KEY", "gr-1")
    monkeypatch.setenv("TOGETHER_API_KEY", "tg-1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-1")
    monkeypatch.setenv("XAI_API_KEY", "xa-1")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-1")

    cases = [
        (openai(), "https://api.openai.com/v1"),
        (openrouter(), "https://openrouter.ai/api/v1"),
        (groq(), "https://api.groq.com/openai/v1"),
        (together(), "https://api.together.xyz/v1"),
        (deepseek(), "https://api.deepseek.com/v1"),
        (xai(), "https://api.x.ai/v1"),
        (ollama(), "http://localhost:11434/v1"),
        (lm_studio(), "http://localhost:1234/v1"),
    ]
    for client, expected_url in cases:
        assert client._base_url == expected_url, f"{client._provider_label} {client._base_url} != {expected_url}"
