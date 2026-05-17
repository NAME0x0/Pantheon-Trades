"""Retrieval-augmented examples for council agents.

Goal: when deliberating on a new market, surface ``k`` *resolved* markets
whose narrative is similar so each agent can ground its forecast in
concrete history. This is intentionally a thin, in-tree implementation
with an optional ChromaDB-backed store for production use.

The public surface is:

  - :class:`ResolvedExample` — one resolved market memo.
  - :class:`VectorStore` (Protocol) — generic vector store interface.
  - :class:`InMemoryVectorStore` — default, no external deps.
  - :class:`ChromaVectorStore` — optional, imported lazily.
  - :func:`retrieve_similar` — top-level helper.
"""

from apollo.rag.examples import ResolvedExample
from apollo.rag.store import (
    ChromaVectorStore,
    InMemoryVectorStore,
    VectorStore,
    retrieve_similar,
)

__all__ = [
    "ResolvedExample",
    "VectorStore",
    "InMemoryVectorStore",
    "ChromaVectorStore",
    "retrieve_similar",
]
