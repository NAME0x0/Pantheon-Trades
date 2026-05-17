"""Pluggable vector store for resolved-market examples.

Two implementations:

  - :class:`InMemoryVectorStore` — pure-Python, no dependencies. Uses
    cosine similarity over caller-supplied or hashed-bag embeddings.
    Default for tests and small dev environments.
  - :class:`ChromaVectorStore` — lazy import of `chromadb`. Identical
    interface but persists to disk and scales to millions of rows.
    Recommended for production: pair with sentence-transformers
    ``all-MiniLM-L6-v2`` for embeddings.

Embedding is decoupled from the store via a ``Callable[[str], list[float]]``.
The default ``hash_bag_embedding`` is a coarse bag-of-words sketch — fine
for the in-memory fallback, replace with a real sentence-transformer in
production.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from apollo.rag.examples import ResolvedExample

Embedder = Callable[[str], list[float]]
DEFAULT_EMBED_DIM = 256


def hash_bag_embedding(text: str, dim: int = DEFAULT_EMBED_DIM) -> list[float]:
    """Bag-of-tokens hashed-feature embedding.

    Coarse but deterministic. Words are normalised to lowercase, hashed
    into ``dim`` buckets, and L2-normalised. Adequate for the default
    in-memory store; not a substitute for a real embedder.
    """
    if not text:
        return [0.0] * dim
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    vec = [0.0] * dim
    for tok in tokens:
        h = hashlib.blake2s(tok.encode("utf-8"), digest_size=4).digest()
        bucket = int.from_bytes(h, "little") % dim
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: Iterable[float], b: Iterable[float]) -> float:
    a_list = list(a)
    b_list = list(b)
    if len(a_list) != len(b_list):
        raise ValueError("vector dimension mismatch")
    num = sum(x * y for x, y in zip(a_list, b_list))
    da = math.sqrt(sum(x * x for x in a_list))
    db = math.sqrt(sum(y * y for y in b_list))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


@dataclass(frozen=True)
class Hit:
    example: ResolvedExample
    score: float


@runtime_checkable
class VectorStore(Protocol):
    def add(self, example: ResolvedExample) -> None: ...
    def query(self, text: str, k: int = 5, *, category: str | None = None) -> list[Hit]: ...
    def __len__(self) -> int: ...


class InMemoryVectorStore:
    """Pure-Python cosine index. Single-process, in-memory only."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self._embedder = embedder or hash_bag_embedding
        self._rows: list[tuple[ResolvedExample, list[float]]] = []

    def add(self, example: ResolvedExample) -> None:
        text = f"{example.question}\n{example.notes}"
        self._rows.append((example, self._embedder(text)))

    def add_many(self, examples: Iterable[ResolvedExample]) -> None:
        for e in examples:
            self.add(e)

    def query(self, text: str, k: int = 5, *, category: str | None = None) -> list[Hit]:
        if not self._rows or k <= 0:
            return []
        q = self._embedder(text)
        scored: list[Hit] = []
        for example, vec in self._rows:
            if category is not None and example.category != category:
                continue
            scored.append(Hit(example=example, score=cosine(q, vec)))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]

    def __len__(self) -> int:
        return len(self._rows)


class ChromaVectorStore:
    """ChromaDB-backed store (lazy import)."""

    def __init__(
        self,
        persist_path: Path,
        collection: str = "pantheon-resolved",
        embedder: Embedder | None = None,
    ) -> None:
        try:
            import chromadb  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "chromadb is not installed; "
                "run `uv add chromadb` in the apollo service"
            ) from e
        import chromadb as _chroma

        persist_path.mkdir(parents=True, exist_ok=True)
        self._client = _chroma.PersistentClient(path=str(persist_path))
        self._col = self._client.get_or_create_collection(collection)
        self._embedder = embedder or hash_bag_embedding

    def add(self, example: ResolvedExample) -> None:
        text = f"{example.question}\n{example.notes}"
        self._col.add(
            ids=[example.market_id],
            documents=[text],
            embeddings=[self._embedder(text)],
            metadatas=[
                {
                    "category": example.category,
                    "outcome": example.outcome,
                    "final_yes_price": example.final_yes_price,
                    "resolved_at": example.resolved_at.isoformat(),
                    "question": example.question,
                    "notes": example.notes,
                    "days_to_resolution_at_listing": (
                        example.days_to_resolution_at_listing
                        if example.days_to_resolution_at_listing is not None
                        else -1.0
                    ),
                }
            ],
        )

    def query(self, text: str, k: int = 5, *, category: str | None = None) -> list[Hit]:
        if k <= 0:
            return []
        where = {"category": category} if category else None
        res = self._col.query(
            query_embeddings=[self._embedder(text)],
            n_results=k,
            where=where,
        )
        hits: list[Hit] = []
        ids = (res.get("ids") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
        from datetime import datetime

        for mid, meta, dist in zip(ids, metas, dists):
            days_field = meta.get("days_to_resolution_at_listing", -1.0)
            days = float(days_field) if days_field is not None and float(days_field) >= 0 else None
            example = ResolvedExample(
                market_id=mid,
                question=str(meta.get("question", "")),
                category=str(meta.get("category", "")),
                resolved_at=datetime.fromisoformat(str(meta.get("resolved_at"))),
                final_yes_price=float(meta.get("final_yes_price", 0.0)),
                outcome=int(meta.get("outcome", 0)),
                days_to_resolution_at_listing=days,
                notes=str(meta.get("notes", "")),
            )
            # Chroma returns distance; convert to a similarity in [0, 1].
            score = 1.0 / (1.0 + float(dist))
            hits.append(Hit(example=example, score=score))
        return hits

    def __len__(self) -> int:
        return self._col.count()


def retrieve_similar(
    store: VectorStore,
    question: str,
    k: int = 5,
    *,
    category: str | None = None,
) -> list[ResolvedExample]:
    """Convenience wrapper returning just the examples, no scores."""
    return [hit.example for hit in store.query(question, k=k, category=category)]
