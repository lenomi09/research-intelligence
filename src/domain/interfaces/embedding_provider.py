"""The EmbeddingProvider interface (see architecture.md §2.3/§8, ADR-015).

Mirrors DocumentParser's pattern: an ABC plus a small domain exception, no vendor
types leaked. Sprint 2's only implementation is FastEmbedProvider
(src/infrastructure/embeddings/fastembed_provider.py); nothing outside
src/infrastructure/embeddings may import an embedding library directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

Vector = list[float]


class EmbeddingError(Exception):
    """Raised when embedding text fails (e.g. the model failed to load/download)."""


class EmbeddingProvider(ABC):
    """Embeds text into fixed-dimensional vectors for similarity search.

    Implementations must be deterministic (same text -> same vector, no per-call
    randomness) and must report their vector dimensionality via ``dimension`` so a
    VectorStore collection can be created with a matching size (RET-002).
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[Vector]:
        """Embed a batch of chunk texts (indexing-time)."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> Vector:
        """Embed a single query string (query-time).

        Kept separate from ``embed_documents`` because some models (including BGE)
        use an asymmetric query/passage embedding scheme — a query needs different
        prompting than the passages it is compared against.
        """
        raise NotImplementedError
