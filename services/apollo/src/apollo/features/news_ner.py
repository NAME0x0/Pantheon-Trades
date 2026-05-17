"""News-NER → market matcher.

When a news headline mentions an entity (a politician, company, ticker,
sports team), we want to short-circuit the normal pipeline and fast-
track an Apollo refresh on every prediction market about that entity.

Two extraction paths, in priority order:

  1. **spaCy** if installed — `en_core_web_sm` for proper-noun entities
     (PERSON, ORG, GPE, EVENT, etc.). Lazy-imported, no startup cost
     when spaCy is absent.
  2. **Regex fallback** — simple capitalised-token sequences plus a
     ticker pattern. Less precise but never blocks the pipeline.

Matching is a normalised token-overlap score between the extracted
entities and each market question. Markets above ``MATCH_THRESHOLD``
are flagged for fast-track scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Capitalised-word sequences like "Donald Trump" or "Bank of America".
_CAP_SEQ_RE = re.compile(r"\b[A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){0,4}\b")
# Stock-ticker pattern: 1-5 uppercase letters, optionally prefixed by $.
_TICKER_RE = re.compile(r"\$?\b([A-Z]{2,5})\b")
# Filler words to drop from extracted phrases.
_STOPWORDS = {
    "The", "A", "An", "And", "Or", "But", "It", "Is", "On", "In", "Of", "To", "By",
    "For", "With", "From", "At", "As", "This", "That", "These", "Those",
    "Said", "Says", "After", "Before", "Will", "Be", "Has", "Have", "Had",
    "Mr", "Mrs", "Ms",
}

MATCH_THRESHOLD = 0.40


@dataclass(frozen=True)
class Entity:
    text: str
    label: str  # PERSON / ORG / GPE / TICKER / EVENT / MISC


@dataclass(frozen=True)
class MatchedMarket:
    market_id: str
    question: str
    score: float
    matched_entities: tuple[str, ...]


def extract_entities(headline: str) -> list[Entity]:
    """Return entities from the headline. Tries spaCy first, then regex."""
    if not headline or not headline.strip():
        return []
    out = _extract_via_spacy(headline)
    if out is not None:
        return out
    return _extract_via_regex(headline)


def _extract_via_spacy(headline: str) -> list[Entity] | None:
    from importlib.util import find_spec

    if find_spec("spacy") is None:
        return None
    try:
        nlp = _spacy_pipeline()
    except OSError:
        # Model not downloaded — caller can `python -m spacy download en_core_web_sm`.
        return None
    doc = nlp(headline)
    return [Entity(text=ent.text, label=ent.label_) for ent in doc.ents]


def _spacy_pipeline():
    """Module-level cache for the spaCy pipeline to amortise load."""
    import spacy  # type: ignore[import-not-found]  # noqa: PLC0415

    global _NLP_SINGLETON  # noqa: PLW0603
    if _NLP_SINGLETON is None:
        _NLP_SINGLETON = spacy.load("en_core_web_sm")
    return _NLP_SINGLETON


_NLP_SINGLETON = None


def _extract_via_regex(headline: str) -> list[Entity]:
    seen: set[str] = set()
    out: list[Entity] = []
    # Tickers first so a sigil-prefixed ALL CAPS word wins TICKER over MISC.
    for m in _TICKER_RE.finditer(headline):
        ticker = m.group(1)
        if ticker in _STOPWORDS:
            continue
        is_dollar = headline[max(0, m.start() - 1) : m.start()] == "$"
        if not is_dollar and len(ticker) > 4:
            continue
        if ticker in seen:
            continue
        seen.add(ticker)
        out.append(Entity(text=ticker, label="TICKER"))
    # Capitalised sequences -> PERSON / ORG / GPE (we cannot tell which).
    for m in _CAP_SEQ_RE.finditer(headline):
        phrase = m.group(0)
        # Strip leading/trailing stopwords.
        words = phrase.split()
        while words and words[0] in _STOPWORDS:
            words.pop(0)
        while words and words[-1] in _STOPWORDS:
            words.pop()
        if len(words) < 1:
            continue
        cleaned = " ".join(words)
        if cleaned in _STOPWORDS or len(cleaned) < 3:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(Entity(text=cleaned, label="MISC"))
    return out


def match_markets(
    entities: list[Entity],
    markets: list[dict],
    *,
    threshold: float = MATCH_THRESHOLD,
) -> list[MatchedMarket]:
    """Score each market question against the entity set.

    ``markets`` entries must carry ``market_id`` and ``question``.
    Score is the fraction of entity tokens present in the question
    (lowercased token-set Jaccard biased toward entity coverage).
    """
    if not entities or not markets:
        return []
    entity_tokens: set[str] = set()
    entity_phrases: list[str] = []
    for e in entities:
        text = e.text.lower()
        entity_phrases.append(text)
        entity_tokens.update(text.split())
    if not entity_tokens:
        return []
    out: list[MatchedMarket] = []
    for m in markets:
        question = str(m.get("question", "")).lower()
        if not question:
            continue
        q_tokens = set(re.findall(r"[a-z0-9]+", question))
        overlap = len(entity_tokens & q_tokens)
        if overlap == 0:
            continue
        score = overlap / len(entity_tokens)
        if score < threshold:
            continue
        matched = tuple(p for p in entity_phrases if any(w in q_tokens for w in p.split()))
        out.append(
            MatchedMarket(
                market_id=str(m.get("market_id", "")),
                question=str(m.get("question", "")),
                score=round(score, 3),
                matched_entities=matched,
            )
        )
    out.sort(key=lambda r: r.score, reverse=True)
    return out
