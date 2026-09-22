"""Unit tests for RetrievalPipeline orchestration, using fake EmbeddingProvider/
VectorStore (mirrors tests/unit/test_pipeline.py's _FakeParser pattern)."""

from __future__ import annotations

from src.domain.interfaces.embedding_provider import EmbeddingProvider, Vector
from src.domain.interfaces.vector_store import ScoredChunk, VectorRecord, VectorStore
from src.retrieval.retrieval import RetrievalPipeline


class _FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.embed_documents_calls: list[list[str]] = []
        self.embed_query_calls: list[str] = []

    @property
    def dimension(self) -> int:
        return 1

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        self.embed_documents_calls.append(texts)
        return [[0.0] for _ in texts]

    def embed_query(self, text: str) -> Vector:
        self.embed_query_calls.append(text)
        return [1.0]


class _FakeVectorStore(VectorStore):
    def __init__(self, hits: list[ScoredChunk] | None = None) -> None:
        self._hits = hits or []
        self.query_calls: list[tuple[Vector, int, list[str] | None]] = []

    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    def query(
        self, vector: Vector, top_k: int = 5, paper_ids: list[str] | None = None
    ) -> list[ScoredChunk]:
        self.query_calls.append((vector, top_k, paper_ids))
        return self._hits

    def delete_paper(self, paper_id: str) -> None:
        raise NotImplementedError


def test_retrieve_uses_embed_query_not_embed_documents() -> None:
    embedder = _FakeEmbeddingProvider()
    pipeline = RetrievalPipeline(embedding_provider=embedder, vector_store=_FakeVectorStore())

    pipeline.retrieve("What dataset was used?")

    assert embedder.embed_query_calls == ["What dataset was used?"]
    assert embedder.embed_documents_calls == []


def test_retrieve_passes_top_k_and_paper_ids_through() -> None:
    store = _FakeVectorStore()
    pipeline = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=store
    )

    pipeline.retrieve("question", top_k=3, paper_ids=["paper_a", "paper_b"])

    vector, top_k, paper_ids = store.query_calls[0]
    assert top_k == 3
    assert paper_ids == ["paper_a", "paper_b"]


def test_retrieve_maps_scored_chunks_to_evidence_chunks() -> None:
    hits = [ScoredChunk(chunk_id="c1", paper_id="paper_a", page=4, text="evidence", score=0.9)]
    store = _FakeVectorStore(hits=hits)
    pipeline = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=store
    )

    results = pipeline.retrieve("question")

    assert len(results) == 1
    assert results[0].paper_id == "paper_a"
    assert results[0].page == 4
    assert results[0].chunk_id == "c1"
    assert results[0].text == "evidence"
    assert results[0].score == 0.9


def test_retrieve_on_empty_store_returns_empty_list_without_raising() -> None:
    pipeline = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=_FakeVectorStore(hits=[])
    )

    assert pipeline.retrieve("question") == []
