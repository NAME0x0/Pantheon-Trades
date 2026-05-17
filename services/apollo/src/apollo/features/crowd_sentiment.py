"""Lexicon-based crowd-sentiment scorer for Nitter feeds.

VADER is the popular open-source baseline; we keep the dependency
surface tiny by shipping a small built-in lexicon and a compatible API.
For production, swap `_score_text` for ``SentimentIntensityAnalyzer``
from `vaderSentiment` (BSD) — same shape, larger lexicon.

API:
  - :func:`score_text(text) -> float in [-1, 1]`
  - :func:`aggregate(tweets) -> CrowdSentiment` with mean, count, and
    a coarse distribution (positive / neutral / negative shares).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# Small, conservative lexicon. Weights roughly mirror VADER convention.
POSITIVE: dict[str, float] = {
    "moon": 2.5, "bullish": 2.0, "rally": 1.5, "breakout": 1.5, "surge": 1.5,
    "win": 1.5, "winning": 1.5, "gain": 1.0, "gains": 1.0, "rising": 1.0,
    "up": 0.8, "strong": 1.0, "good": 1.0, "great": 1.5, "excellent": 2.0,
    "amazing": 2.0, "perfect": 2.0, "love": 1.5, "buy": 1.0, "long": 1.0,
    "rocket": 2.0, "explode": 1.5,
}
NEGATIVE: dict[str, float] = {
    "dump": -2.0, "bearish": -2.0, "crash": -2.5, "fall": -1.0, "falling": -1.0,
    "loss": -1.5, "losses": -1.5, "down": -0.8, "weak": -1.0, "bad": -1.0,
    "terrible": -2.0, "awful": -2.0, "hate": -1.5, "sell": -1.0, "short": -1.0,
    "collapse": -2.5, "rug": -2.5, "scam": -2.5, "dead": -1.5, "fail": -1.5,
}
NEGATORS = {"not", "no", "never", "without", "isn't", "wasn't", "aren't", "didn't"}
INTENSIFIERS = {"very": 1.5, "extremely": 1.8, "really": 1.3, "super": 1.4}

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


def score_text(text: str) -> float:
    """Compound sentiment in roughly [-1, 1] via lexicon + negation + intensifiers."""
    if not text:
        return 0.0
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return 0.0
    score = 0.0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in POSITIVE or tok in NEGATIVE:
            base = POSITIVE.get(tok, 0.0) + NEGATIVE.get(tok, 0.0)
            mult = 1.0
            # Look back two tokens for negators or intensifiers.
            for j in (i - 1, i - 2):
                if j < 0:
                    continue
                prev = tokens[j]
                if prev in NEGATORS:
                    mult *= -1.0
                elif prev in INTENSIFIERS:
                    mult *= INTENSIFIERS[prev]
            score += base * mult
        i += 1
    # Crude normalisation — divide by an approximate token magnitude.
    denom = max(1.0, (score * score + 15.0) ** 0.5)
    return max(-1.0, min(1.0, score / denom))


@dataclass(frozen=True)
class CrowdSentiment:
    mean_score: float
    sample_count: int
    positive_share: float
    neutral_share: float
    negative_share: float


def aggregate(tweets: Iterable) -> CrowdSentiment:
    """Aggregate a list of tweets into a compound sentiment view."""
    scores: list[float] = []
    for tw in tweets:
        text = getattr(tw, "clean_text", None) or getattr(tw, "text", "") or ""
        scores.append(score_text(text))
    if not scores:
        return CrowdSentiment(0.0, 0, 0.0, 1.0, 0.0)
    n = len(scores)
    pos = sum(1 for s in scores if s > 0.1)
    neg = sum(1 for s in scores if s < -0.1)
    neu = n - pos - neg
    return CrowdSentiment(
        mean_score=sum(scores) / n,
        sample_count=n,
        positive_share=pos / n,
        neutral_share=neu / n,
        negative_share=neg / n,
    )
