"""Robust parser for the structured vote block every council agent emits.

The format we ask each agent to produce:

    VOTE: APPROVE | REJECT | ABSTAIN
    CONFIDENCE: 0.XX
    PROBABILITY: 0.XX
    FLAGS: comma,separated,flags | NONE
    REASON: free text (one line)

Agents will deviate (extra prose, percent signs, casing) so this parser is
deliberately forgiving: anything malformed falls back to ABSTAIN at 0.5/0.5
rather than crashing the debate. We always clamp probability and confidence
into [0, 1] so downstream math stays well-defined.
"""

from __future__ import annotations

import re

_VOTE_RX = re.compile(r"^\s*VOTE\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_CONF_RX = re.compile(r"^\s*CONFIDENCE\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_PROB_RX = re.compile(r"^\s*PROBABILITY\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_FLAGS_RX = re.compile(r"^\s*FLAGS\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def _clamp01(v: float) -> float:
    if v != v:  # NaN
        return 0.5
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _parse_float(raw: str) -> float | None:
    raw = raw.strip().rstrip("%").rstrip(".").strip()
    if not raw:
        return None
    try:
        v = float(raw)
    except ValueError:
        return None
    if v > 1.0:
        v = v / 100.0
    return v


def parse_vote(text: str) -> tuple[str, float, float, list[str]]:
    """Parse a structured vote block into (vote, confidence, probability, flags)."""
    vote = "ABSTAIN"
    confidence = 0.5
    probability = 0.5
    flags: list[str] = []

    m = _VOTE_RX.search(text)
    if m:
        token = m.group(1).strip().upper()
        token = token.split()[0] if token else ""
        if token in ("APPROVE", "REJECT", "ABSTAIN"):
            vote = token

    m = _CONF_RX.search(text)
    if m:
        v = _parse_float(m.group(1))
        if v is not None:
            confidence = _clamp01(v)

    m = _PROB_RX.search(text)
    if m:
        v = _parse_float(m.group(1))
        if v is not None:
            probability = _clamp01(v)

    m = _FLAGS_RX.search(text)
    if m:
        raw = m.group(1).strip()
        if raw.upper() not in ("NONE", "N/A", ""):
            flags = [f.strip() for f in raw.split(",") if f.strip()]

    return vote, confidence, probability, flags


# Back-compat alias for the original underscored name.
_parse_vote = parse_vote
