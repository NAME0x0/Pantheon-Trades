"""Tests for headline-NER and market matching."""

from __future__ import annotations

from apollo.features.news_ner import (
    Entity,
    extract_entities,
    match_markets,
)


def test_extract_capitalised_phrases():
    ents = extract_entities("Donald Trump signs executive order on tariffs")
    names = [e.text for e in ents]
    assert "Donald Trump" in names


def test_extract_strips_leading_stopwords():
    ents = extract_entities("The Fed raised rates by 25 bps")
    names = {e.text for e in ents}
    assert "Fed" in names
    # "The Fed" should not appear with the article preserved.
    assert "The Fed" not in names


def test_extract_ticker_with_sigil():
    ents = extract_entities("$AAPL surges 5% after earnings beat")
    labels = {(e.text, e.label) for e in ents}
    assert ("AAPL", "TICKER") in labels


def test_extract_ticker_naked_short_word():
    ents = extract_entities("TSLA tumbles on weak deliveries")
    labels = {e.text for e in ents}
    assert "TSLA" in labels


def test_extract_skips_long_uppercase_acronyms():
    # 6 letters without $ should NOT be classified as a ticker.
    ents = extract_entities("NASDAQQ rallies broadly")
    tickers = [e.text for e in ents if e.label == "TICKER"]
    assert "NASDAQQ" not in tickers


def test_extract_empty_input():
    assert extract_entities("") == []
    assert extract_entities("   ") == []


def test_match_markets_above_threshold():
    entities = [Entity("Donald Trump", "MISC"), Entity("tariffs", "MISC")]
    markets = [
        {"market_id": "m1", "question": "Will Donald Trump impose tariffs on China?"},
        {"market_id": "m2", "question": "Will SpaceX launch Starship in May?"},
    ]
    hits = match_markets(entities, markets, threshold=0.3)
    assert len(hits) == 1
    assert hits[0].market_id == "m1"
    assert hits[0].score >= 0.3


def test_match_markets_threshold_filters():
    entities = [Entity("Donald Trump", "MISC")]
    markets = [
        {"market_id": "m1", "question": "Will Trump win New Hampshire?"},
    ]
    # Trump matches 'trump' -> 1/2 entity tokens overlap = 0.5; passes 0.4.
    hits = match_markets(entities, markets, threshold=0.4)
    assert len(hits) == 1
    # Now with threshold 0.6 it should drop.
    hits_strict = match_markets(entities, markets, threshold=0.6)
    assert hits_strict == []


def test_match_markets_sorted_desc():
    entities = [Entity("Donald Trump", "MISC")]
    markets = [
        {"market_id": "m1", "question": "Donald wins"},
        {"market_id": "m2", "question": "Trump wins"},
        {"market_id": "m3", "question": "Donald Trump wins"},
    ]
    hits = match_markets(entities, markets, threshold=0.1)
    scores = [h.score for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_match_markets_no_entities():
    assert match_markets([], [{"market_id": "m1", "question": "any"}]) == []


def test_match_markets_no_markets():
    assert match_markets([Entity("X", "MISC")], []) == []


def test_match_markets_handles_missing_question_field():
    hits = match_markets(
        [Entity("Bitcoin", "MISC")],
        [{"market_id": "m1"}, {"market_id": "m2", "question": "Bitcoin"}],
    )
    assert {h.market_id for h in hits} == {"m2"}
