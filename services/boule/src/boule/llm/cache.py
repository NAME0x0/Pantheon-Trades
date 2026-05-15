"""Persistent disk cache for LLM completions.

The Boule council fires ~31 calls per deliberation (10 R1 + 10 R2 +
Athena synthesis + 10 R4). On a fixed demo signal (the BTC $120k
scenario), re-running the council should produce identical outputs
because every LLM input is identical — yet the previous behaviour
burned the daily quota every single time.

This cache fixes that. Keys are sha256 of (model, system prompt,
messages, max_tokens). Values are JSON-serialised CompletionResults
stored under ``.cache/boule-llm/<key>.json`` relative to the working
directory. A cache hit returns instantly with zero network calls.

Disable with ``BOULE_LLM_CACHE=0`` if you genuinely want every run
to hit the provider.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from boule.llm.base import CompletionResult

CACHE_ENV = "BOULE_LLM_CACHE"
CACHE_DIR_ENV = "BOULE_LLM_CACHE_DIR"


def _enabled() -> bool:
    return os.environ.get(CACHE_ENV, "1") not in ("0", "false", "False", "")


def _cache_dir() -> Path:
    override = os.environ.get(CACHE_DIR_ENV)
    if override:
        return Path(override)
    return Path.cwd() / ".cache" / "boule-llm"


def cache_key(
    *,
    provider: str,
    model: str,
    system: str,
    messages: list[dict],
    max_tokens: int,
) -> str:
    """Deterministic hash over the inputs that fully define the call."""
    payload = json.dumps(
        {
            "provider": provider,
            "model": model,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get(key: str) -> Optional[CompletionResult]:
    if not _enabled():
        return None
    p = _cache_dir() / f"{key}.json"
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return CompletionResult(text=raw["text"], tokens=int(raw.get("tokens", 0)))
    except Exception:
        return None


def put(key: str, result: CompletionResult) -> None:
    if not _enabled():
        return
    try:
        d = _cache_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{key}.json").write_text(
            json.dumps({"text": result.text, "tokens": result.tokens}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        # cache miss is never fatal
        pass
