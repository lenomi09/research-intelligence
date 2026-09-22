"""The VectorStore interface (see architecture.md §2.3/§8, ADR-004, ADR-015).

Mirrors DocumentParser's pattern: an ABC plus small result types and a domain
exception, no vendor types leaked. Sprint 2's only implementation is
QdrantLocalVectorStore (src/infrastructure/vector_stores/qdrant_local_store.py);
nothing outside src/infrastructure/vector_stores may import a vector-store client
directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NamedTuple

from src.domain.interfaces.embedding_provider import Vector


class VectorRecord(NamedTuple):
    """One upsertable point: an embedded chunk plus the payload needed to
    reconstruct a citation without a second lookup."""

    chunk_id: str
    vector: Vector
    paper_id: str
    page: int
    text: str


class ScoredChunk(NamedTuple):
    """One search result: a chunk plus its similarity score."""

    chunk_id: str
    paper_id: str
    page: int
    text: str
    score: float


class VectorStoreError(Exception):
    """Raised when the underlying store cannot be reached or is misconfigured
    (e.g. a dimension mismatch between the store and the configured EmbeddingProvider)."""


class VectorStore(ABC):
    """Upsert + top-K similarity query with paper-scoped filtering (RET-002)."""

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def query(
        self, vector: Vector, top_k: int = 5, paper_ids: list[str] | None = None
    ) -> list[ScoredChunk]:
        """Return up to ``top_k`` nearest chunks, ranked by similarity score
        descending. If ``paper_ids`` is given, restrict the search to chunks from
        those papers only (collection-scoped when ``None``, paper-scoped otherwise
        — see architecture.md §4.2)."""
        raise NotImplementedError

    @abstractmethod
    def delete_paper(self, paper_id: str) -> None:
        """Remove every chunk belonging to one paper.

        Needed for idempotent re-indexing: without this, re-running the indexing
        pipeline for a paper whose content changed (or simply re-running it at all)
        would accumulate duplicate/stale points in the store.
        """
        raise NotImplementedError
