"""Tests for the Wikipedia entity resolver.

Hermetic — uses an in-process fake LLM that returns canned responses.
We test:
  - Valid output passes through.
  - "NONE" output → article=None.
  - Spaces / quotes / URLs / multi-line / non-ASCII rejected.
  - Batch concurrency is bounded by the semaphore.
  - applicability_rate computes correctly.
"""

from __future__ import annotations

import asyncio

import pytest

from apollo.entity_resolver import (
    Resolution,
    _validate_title,
    applicability_rate,
    resolve_batch,
    resolve_one,
)


def test_validate_title_passes_canonical():
    assert _validate_title("Bitcoin") == "Bitcoin"
    assert _validate_title("Donald_Trump") == "Donald_Trump"
    assert _validate_title("Los_Angeles_Lakers") == "Los_Angeles_Lakers"
    assert _validate_title("Tesla,_Inc.") == "Tesla,_Inc"  # trailing dot stripped


def test_validate_title_strips_whitespace():
    assert _validate_title("  Bitcoin  \n") == "Bitcoin"


def test_validate_title_takes_first_line_only():
    assert _validate_title("Bitcoin\nExtra prose") == "Bitcoin"


def test_validate_title_none_is_none():
    assert _validate_title("NONE") is None
    assert _validate_title("none") is None
    assert _validate_title("  NONE  ") is None


def test_validate_title_rejects_empty():
    assert _validate_title("") is None
    assert _validate_title("   ") is None


def test_validate_title_rejects_with_spaces():
    """We asked for underscores. Title with spaces is malformed."""
    assert _validate_title("Donald Trump") is None


def test_validate_title_rejects_url():
    assert _validate_title("https://en.wikipedia.org/wiki/Bitcoin") is None


def test_validate_title_rejects_markdown():
    assert _validate_title("**Bitcoin**") is None
    assert _validate_title("`Bitcoin`") is None
    assert _validate_title("[Bitcoin]") is None


def test_validate_title_rejects_quotes():
    assert _validate_title('"Bitcoin"') is None


def test_validate_title_strips_trailing_punctuation():
    assert _validate_title("Bitcoin.") == "Bitcoin"
    assert _validate_title("Bitcoin,") == "Bitcoin"


@pytest.mark.asyncio
async def test_resolve_one_happy_path():
    async def fake_llm(system, user):
        return {"text": "Bitcoin"}
    r = await resolve_one("Will BTC be above $120k?", llm_call=fake_llm)
    assert r.article == "Bitcoin"
    assert r.question == "Will BTC be above $120k?"


@pytest.mark.asyncio
async def test_resolve_one_returns_none_when_llm_says_none():
    async def fake_llm(system, user):
        return {"text": "NONE"}
    r = await resolve_one("Will I clean my room?", llm_call=fake_llm)
    assert r.article is None


@pytest.mark.asyncio
async def test_resolve_one_handles_empty_llm_text():
    async def fake_llm(system, user):
        return {"text": ""}
    r = await resolve_one("Q?", llm_call=fake_llm)
    assert r.article is None


@pytest.mark.asyncio
async def test_resolve_one_rejects_malformed_with_spaces():
    async def fake_llm(system, user):
        return {"text": "Donald Trump"}  # missing underscores
    r = await resolve_one("Will Trump win?", llm_call=fake_llm)
    assert r.article is None


@pytest.mark.asyncio
async def test_resolve_batch_returns_one_per_question():
    titles = ["Bitcoin", "Donald_Trump", "NONE", "Tesla,_Inc"]

    async def fake_llm(system, user):
        # Return next title per question text
        for q, t in zip(_QUESTIONS, titles):
            if q in user:
                return {"text": t}
        return {"text": "NONE"}

    global _QUESTIONS
    _QUESTIONS = ["BTC", "Trump", "weather", "Tesla"]
    out = await resolve_batch(_QUESTIONS, llm_call=fake_llm, concurrency=2)
    assert len(out) == 4
    assert out[0].article == "Bitcoin"
    assert out[1].article == "Donald_Trump"
    assert out[2].article is None
    # Trailing punctuation stripped to canonical form
    assert out[3].article == "Tesla,_Inc"


@pytest.mark.asyncio
async def test_resolve_batch_catches_exceptions():
    async def bad_llm(system, user):
        raise RuntimeError("offline")

    out = await resolve_batch(["q1", "q2"], llm_call=bad_llm, concurrency=2)
    assert all(r.article is None for r in out)
    assert all("ERROR" in r.raw_response for r in out)


def test_applicability_rate_handles_empty():
    assert applicability_rate([]) == 0.0


def test_applicability_rate_basic():
    rs = [
        Resolution(question="q1", article="A"),
        Resolution(question="q2", article=None),
        Resolution(question="q3", article="B"),
        Resolution(question="q4", article="C"),
    ]
    assert applicability_rate(rs) == 0.75


def test_resolve_batch_concurrency_capped():
    """The semaphore prevents more than ``concurrency`` calls running
    simultaneously. We verify by counting peak concurrency."""
    state = {"in_flight": 0, "peak": 0}

    async def slow_llm(system, user):
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        await asyncio.sleep(0.02)
        state["in_flight"] -= 1
        return {"text": "Bitcoin"}

    asyncio.run(resolve_batch(["q"] * 8, llm_call=slow_llm, concurrency=3))
    assert state["peak"] <= 3
