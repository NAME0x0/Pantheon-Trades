"""Unit tests for the in-memory RAG store + hashing embedder."""

from __future__ import annotations

from datetime import datetime, timezone

from apollo.rag import (
    InMemoryVectorStore,
    ResolvedExample,
    retrieve_similar,
)
from apollo.rag.store import cosine, hash_bag_embedding


def _ex(question: str, category: str = "politics", outcome: int = 1, market_id: str | None = None) -> ResolvedExample:
    return ResolvedExample(
        market_id=market_id or f"m-{abs(hash(question))}",
        question=question,
        category=category,
        resolved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        final_yes_price=0.97 if outcome == 1 else 0.03,
        outcome=outcome,
        days_to_resolution_at_listing=30.0,
        notes="",
    )


def test_empty_store_returns_no_hits():
    store = InMemoryVectorStore()
    assert store.query("anything", k=5) == []
    assert len(store) == 0


def test_top_hit_matches_exact_query():
    store = InMemoryVectorStore()
    store.add(_ex("Will Bitcoin hit 100k by year end?"))
    store.add(_ex("Will the Fed cut rates in June?"))
    store.add(_ex("Will Lakers win the championship?", category="sports"))
    hits = store.query("Will Bitcoin reach 100000 by year end?", k=3)
    assert len(hits) == 3
    assert hits[0].example.question.startswith("Will Bitcoin")


def test_query_respects_category_filter():
    store = InMemoryVectorStore()
    store.add(_ex("Will Bitcoin hit 100k by year end?", category="crypto"))
    store.add(_ex("Will the Fed cut rates in June?", category="macro"))
    hits = store.query("Bitcoin", k=5, category="macro")
    assert all(h.example.category == "macro" for h in hits)


def test_retrieve_similar_returns_examples():
    store = InMemoryVectorStore()
    store.add(_ex("Will Bitcoin hit 100k by year end?", category="crypto"))
    out = retrieve_similar(store, "Bitcoin 100k by EOY", k=1)
    assert isinstance(out, list)
    assert out[0].category == "crypto"


def test_k_zero_returns_empty():
    store = InMemoryVectorStore()
    store.add(_ex("anything"))
    assert store.query("anything", k=0) == []


def test_hash_bag_embedding_deterministic():
    a = hash_bag_embedding("hello world hello")
    b = hash_bag_embedding("hello world hello")
    assert a == b


def test_hash_bag_embedding_empty_text():
    v = hash_bag_embedding("")
    assert len(v) == 256
    assert all(x == 0.0 for x in v)


def test_hash_bag_embedding_normalised():
    v = hash_bag_embedding("the quick brown fox jumps over the lazy dog")
    norm = sum(x * x for x in v) ** 0.5
    assert abs(norm - 1.0) < 1e-9


def test_cosine_identical_vectors_one():
    v = [1.0, 2.0, 3.0]
    assert abs(cosine(v, v) - 1.0) < 1e-9


def test_cosine_orthogonal_vectors_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_handles_zero_vector():
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_resolved_example_as_prose_yes():
    e = _ex("Will inflation drop below 3%?", outcome=1)
    prose = e.as_prose()
    assert "YES" in prose
    assert "inflation" in prose


def test_resolved_example_as_prose_no():
    e = _ex("Will inflation drop below 3%?", outcome=0)
    prose = e.as_prose()
    assert "NO" in prose


def test_add_many_increments_size():
    store = InMemoryVectorStore()
    store.add_many([_ex(f"q{i}") for i in range(5)])
    assert len(store) == 5
