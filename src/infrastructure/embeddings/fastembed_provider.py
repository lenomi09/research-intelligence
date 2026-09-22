"""EmbeddingProvider implementation backed by fastembed's ONNX runtime (ADR-015).

Chosen over sentence-transformers specifically to avoid a torch dependency — see
ADR-015 for the full reasoning (mirrors ADR-014's PyMuPDF-over-Docling tradeoff).
"""

from __future__ import annotations

from src.domain.interfaces.embedding_provider import (
    EmbeddingError,
    EmbeddingProvider,
    Vector,
)

DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"


class FastEmbedProvider(EmbeddingProvider):
    """EmbeddingProvider backed by ``fastembed.TextEmbedding``.

    Uses ``embed`` (passage-style prompting) for ``embed_documents`` and
    ``query_embed`` (query-style prompting) for ``embed_query`` — BGE models are
    trained with an asymmetric query/passage scheme, and using the wrong one for
    either side measurably hurts retrieval quality.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise EmbeddingError(f"fastembed is not installed: {exc}") from exc

        try:
            self._model = TextEmbedding(model_name=model_name)
        except Exception as exc:  # model load/download failure — see EmbeddingError
            raise EmbeddingError(
                f"failed to load embedding model '{model_name}' (first run needs "
                f"network access to download model weights): {exc}"
            ) from exc

        self._dimension = len(next(iter(self._model.embed(["dimension probe"]))))

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        if not texts:
            return []
        return [vector.tolist() for vector in self._model.embed(texts)]

    def embed_query(self, text: str) -> Vector:
        return next(iter(self._model.query_embed([text]))).tolist()
