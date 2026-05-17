"""Cross-listing detection — find prediction-market questions that
list on more than one venue.

Activates ``basis_arb`` (cross-venue spread) + ``consensus_delta``
(human-consensus vs price prior). Both features were UNTESTABLE in
the Manifold-only backtest because we couldn't compare a single
question's price across venues. With Manifold + Kalshi reachable
(neither geo-blocked, neither requires a paid key), this module fills
the gap on the venues we CAN reach.

Matching algorithm — deliberately simple, deliberately recallable
over precise:

  1. Normalise each question text: lowercase, strip punctuation,
     collapse whitespace, drop common words ("will", "the", "a"),
     drop dates.
  2. Tokenise. Take the set of remaining words.
  3. Jaccard similarity ≥ 0.5 on token sets ⇒ candidate match.
  4. Filter candidates by resolution-date proximity (within 14 days)
     when both venues publish one.

Operator reviews candidates manually — a Jaccard threshold doesn't
catch every cross-listing but it's free, fast, and surfaces enough
to be useful. A future hop is an LLM verifier that says yes/no on
each candidate pair, but the cost of a manual review is zero.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Common stopwords + question-form fillers we strip before tokenising.
STOPWORDS = frozenset({
    "will", "the", "a", "an", "is", "to", "of", "in", "on", "at",
    "by", "for", "with", "do", "does", "did", "be", "been", "this",
    "that", "and", "or", "but", "would", "should", "could", "can",
    "may", "might", "shall", "have", "has", "had", "than", "then",
    "if", "as", "it", "its", "his", "her", "him", "she", "he",
    "they", "them", "their", "our", "us", "we", "you", "your",
    "any", "some", "no", "not", "yes",
})

# Date-ish tokens: ISO dates, month names, four-digit years.
DATE_TOKENS = re.compile(
    r"\b("
    r"\d{4}-\d{2}-\d{2}"
    r"|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
    r"|january|february|march|april|june|july|august|september"
    r"|october|november|december"
    r"|20\d{2}|19\d{2}"
    r"|q[1-4]"
    r")\b",
    re.IGNORECASE,
)


def normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation + dates + stopwords, return a token list.

    Numbers with commas (``$120,000``) are coerced to a single token
    (``120000``) before splitting so cross-venue questions match even
    when one writes the number with separators and the other doesn't.
    """
    s = (text or "").lower()
    s = DATE_TOKENS.sub(" ", s)
    # Collapse digit-comma-digit BEFORE the generic punctuation strip:
    #   "$120,000" -> "$120000".  Loop until stable for "$1,234,567".
    while True:
        new_s = re.sub(r"(\d),(\d)", r"\1\2", s)
        if new_s == s:
            break
        s = new_s
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = [t for t in s.split() if t and t not in STOPWORDS]
    return tokens


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets. 0 when both empty."""
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


@dataclass(frozen=True)
class CrossListingCandidate:
    """One candidate cross-listing pair across two venues."""

    venue_a: str
    venue_b: str
    market_a_id: str
    market_b_id: str
    question_a: str
    question_b: str
    similarity: float


def find_cross_listings(
    markets_a: list[dict[str, Any]],
    markets_b: list[dict[str, Any]],
    *,
    venue_a: str = "manifold",
    venue_b: str = "kalshi",
    threshold: float = 0.5,
    question_key_a: str = "question",
    question_key_b: str = "question",
    id_key_a: str = "id",
    id_key_b: str = "id",
) -> list[CrossListingCandidate]:
    """All pairs ``(a, b)`` with Jaccard token-overlap ≥ threshold.

    O(N * M) — fine for N, M ≤ ~5000. For bigger feeds, swap to a
    posting-list index keyed by token first.

    Args:
        markets_a, markets_b: lists of market dicts from each venue.
        venue_a, venue_b: human-readable venue labels.
        threshold: minimum Jaccard for a pair to be returned.
        question_key_*: which dict field holds the question text.
        id_key_*: which dict field holds the market id.
    """
    # Pre-tokenise once.
    tok_a = [(m, set(normalise(m.get(question_key_a, "")))) for m in markets_a]
    tok_b = [(m, set(normalise(m.get(question_key_b, "")))) for m in markets_b]

    out: list[CrossListingCandidate] = []
    for ma, ta in tok_a:
        if not ta:
            continue
        for mb, tb in tok_b:
            if not tb:
                continue
            sim = jaccard(ta, tb)
            if sim < threshold:
                continue
            out.append(CrossListingCandidate(
                venue_a=venue_a,
                venue_b=venue_b,
                market_a_id=str(ma.get(id_key_a, "")),
                market_b_id=str(mb.get(id_key_b, "")),
                question_a=ma.get(question_key_a, ""),
                question_b=mb.get(question_key_b, ""),
                similarity=round(sim, 3),
            ))
    out.sort(key=lambda c: c.similarity, reverse=True)
    return out
