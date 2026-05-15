"""Tests for the persistent LLM completion cache.

Same prompt + same provider = cache hit + zero network. Crucial because
the council re-runs identical prompts on every deliberation against a
fixed demo signal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from boule.llm.base import CompletionResult
from boule.llm.cache import cache_key, get, put


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BOULE_LLM_CACHE_DIR", str(tmp_path / "boule-llm"))
    monkeypatch.setenv("BOULE_LLM_CACHE", "1")
    yield


def test_key_is_deterministic():
    args = dict(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        system="you are Athena",
        messages=[{"role": "user", "content": "what is the verdict?"}],
        max_tokens=512,
    )
    k1 = cache_key(**args)  # type: ignore[arg-type]
    k2 = cache_key(**args)  # type: ignore[arg-type]
    assert k1 == k2
    assert len(k1) == 64  # sha256 hex


def test_key_changes_with_any_input():
    base = dict(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        system="you are Athena",
        messages=[{"role": "user", "content": "what is the verdict?"}],
        max_tokens=512,
    )
    k0 = cache_key(**base)  # type: ignore[arg-type]
    assert cache_key(**{**base, "provider": "anthropic"}) != k0  # type: ignore[arg-type]
    assert cache_key(**{**base, "model": "claude-sonnet-4-6"}) != k0  # type: ignore[arg-type]
    assert cache_key(**{**base, "system": "you are Zeus"}) != k0  # type: ignore[arg-type]
    assert cache_key(**{**base, "max_tokens": 1024}) != k0  # type: ignore[arg-type]
    assert (
        cache_key(
            **{
                **base,
                "messages": [{"role": "user", "content": "what is the verdict??"}],
            }  # type: ignore[arg-type]
        )
        != k0
    )


def test_get_returns_none_when_missing():
    key = cache_key(
        provider="gemini",
        model="x",
        system="s",
        messages=[{"role": "user", "content": "c"}],
        max_tokens=1,
    )
    assert get(key) is None


def test_round_trip():
    key = cache_key(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        system="be terse",
        messages=[{"role": "user", "content": "vote?"}],
        max_tokens=512,
    )
    put(key, CompletionResult(text="APPROVE p=0.62 c=0.85", tokens=240))
    cached = get(key)
    assert cached is not None
    assert cached.text == "APPROVE p=0.62 c=0.85"
    assert cached.tokens == 240


def test_disabled_via_env(monkeypatch):
    monkeypatch.setenv("BOULE_LLM_CACHE", "0")
    key = cache_key(
        provider="gemini",
        model="x",
        system="s",
        messages=[{"role": "user", "content": "c"}],
        max_tokens=1,
    )
    put(key, CompletionResult(text="hi", tokens=1))
    # With cache disabled both get() and put() are no-ops.
    assert get(key) is None
