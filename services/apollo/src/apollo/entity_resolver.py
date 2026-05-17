"""LLM-driven entity resolver — maps a market question to a canonical
Wikipedia article title.

The XML backtest showed `attention` (Wikipedia pageviews) was the most
generally adoptable source, applying to ~34% of markets. Most of the
remaining 66% had a relevant entity but we couldn't find it because
the question text didn't name it directly.

Examples where naive extraction fails:
  - "Will the FOMC raise rates by 50bp at the May meeting?"
    → entity: ``Federal_Open_Market_Committee``
  - "Will Trump pardon Hunter Biden before Jan 2027?"
    → entity: ``Donald_Trump`` (or ``Hunter_Biden`` — operator chooses)
  - "Will Tesla deliver more than 500k cars in Q3?"
    → entity: ``Tesla,_Inc.``

This module wraps a single LLM call. Operator passes one question;
gets back a candidate Wikipedia title (URL-encoded form with
underscores instead of spaces). Returns ``None`` when no clear entity
maps — e.g. a "Will I have a good day tomorrow?" type market.

Provider-agnostic via boule.llm protocol. Costs ~$0.0001 per question
on Gemini flash-lite.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass


SYSTEM_PROMPT = """You are a Wikipedia-entity resolver for prediction
market questions. For each question:

1. Identify the single most-relevant Wikipedia article that, if the
   operator queried its pageview velocity, would tell us about
   public attention on the underlying event.
2. Output ONLY the URL-form article title (underscores instead of
   spaces, no leading 'wiki/'). One title per line.
3. If no clear entity exists (e.g. "Will I have a good day?", "Will
   we hit 1000 users?"), output the single token NONE.

Strict format. No prose. No quoting. No URLs. No markdown.

Examples:
- "Will Trump pardon Hunter Biden by 2027?" → Donald_Trump
- "Will Bitcoin trade above $120,000 by 2026-12-31?" → Bitcoin
- "Will the Lakers win the 2026 NBA Finals?" → Los_Angeles_Lakers
- "Will the FOMC cut rates 50bp at the May meeting?" → Federal_Open_Market_Committee
- "Will I clean my room this weekend?" → NONE
"""


@dataclass(frozen=True)
class Resolution:
    question: str
    article: str | None  # URL form with underscores, or None
    raw_response: str = ""


def _validate_title(raw: str) -> str | None:
    """Strict guard on the LLM output. Accepts only a single line of
    [A-Za-z0-9_,.-()]+ characters or `NONE`.
    """
    cleaned = raw.strip().split("\n", 1)[0].strip()
    if not cleaned:
        return None
    if cleaned.upper() == "NONE":
        return None
    # Strip a trailing period or comma the model occasionally adds.
    cleaned = cleaned.rstrip(".,")
    if not re.fullmatch(r"[A-Za-z0-9_(),.\-:&'!?]+", cleaned):
        return None
    if " " in cleaned:
        return None  # we asked for underscores
    return cleaned


async def resolve_one(
    question: str,
    *,
    llm_call,  # callable that returns the LLM record dict
) -> Resolution:
    """Resolve a single question. ``llm_call`` is an async function
    accepting (system, user) and returning the standard LLM record
    dict (text, http_status, etc) — keeps this module decoupled from
    any specific provider.
    """
    user = f"Question: {question.strip()}"
    record = await llm_call(SYSTEM_PROMPT, user)
    text = record.get("text", "") or ""
    article = _validate_title(text)
    return Resolution(question=question, article=article, raw_response=text[:160])


async def resolve_batch(
    questions: list[str],
    *,
    llm_call,
    concurrency: int = 4,
) -> list[Resolution]:
    """Resolve many questions in parallel. ``concurrency`` keeps us
    inside any provider's RPM cap — Gemini flash-lite free tier is
    10 RPM, so 4 concurrent + the natural latency per call is safe."""
    sem = asyncio.Semaphore(concurrency)

    async def _bound(q: str) -> Resolution:
        async with sem:
            try:
                return await resolve_one(q, llm_call=llm_call)
            except Exception as exc:  # noqa: BLE001
                return Resolution(question=q, article=None, raw_response=f"ERROR: {exc!r}")

    return await asyncio.gather(*[_bound(q) for q in questions])


def applicability_rate(resolutions: list[Resolution]) -> float:
    """What fraction of questions yielded a usable Wikipedia title?"""
    if not resolutions:
        return 0.0
    hits = sum(1 for r in resolutions if r.article is not None)
    return hits / len(resolutions)
