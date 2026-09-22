"""Unit tests for IndexingPipeline orchestration, using fake PaperSource/
EmbeddingProvider/VectorStore so these don't depend on real fastembed/qdrant-client
(mirrors tests/unit/test_pipeline.py's _FakeParser pattern)."""

from __future__ import annotations

from src.domain.interfaces.embedding_provider import EmbeddingProvider, Vector
from src.domain.interfaces.paper_source import PaperSource
from src.domain.interfaces.vector_store import ScoredChunk, VectorRecord, VectorStore
from src.domain.models.paper import Paper
from src.domain.models.text_block import TextBlock
from src.retrieval.indexing import IndexingPipeline


class _FakePaperSource(PaperSource):
    def __init__(self, papers: list[Paper]):
        self._papers = papers

    def list_papers(self) -> list[Paper]:
        return self._papers


class _FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic fake: each text maps to a 1-dim vector of its length."""

    @property
    def dimension(self) -> int:
        return 1

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        return [[float(len(t))] for t in texts]

    def embed_query(self, text: str) -> Vector:
        return [float(len(text))]


class _FakeVectorStore(VectorStore):
    def __init__(self) -> None:
        self.upsert_calls: list[list[VectorRecord]] = []
        self.deleted_paper_ids: list[str] = []
        self._records: dict[str, VectorRecord] = {}

    def upsert(self, records: list[VectorRecord]) -> None:
        self.upsert_calls.append(records)
        for r in records:
            self._records[r.chunk_id] = r

    def query(
        self, vector: Vector, top_k: int = 5, paper_ids: list[str] | None = None
    ) -> list[ScoredChunk]:
        return []

    def delete_paper(self, paper_id: str) -> None:
        self.deleted_paper_ids.append(paper_id)
        self._records = {k: v for k, v in self._records.items() if v.paper_id != paper_id}


def _paper(paper_id: str, num_blocks: int) -> Paper:
    return Paper(
        paper_id=paper_id,
        source_path="irrelevant.pdf",
        page_count=1,
        metadata_source="unavailable",
        text_blocks=[
            TextBlock(block_id=f"block_{i:04d}", page=1, text=f"text {i}", order=i)
            for i in range(num_blocks)
        ],
    )


def test_index_all_indexes_every_paper_and_reports_counts() -> None:
    papers = [_paper("paper_001", 2), _paper("paper_002", 3)]
    store = _FakeVectorStore()
    pipeline = IndexingPipeline(
        paper_source=_FakePaperSource(papers),
        embedding_provider=_FakeEmbeddingProvider(),
        vector_store=store,
    )

    report = pipeline.index_all()

    assert report.papers_indexed == 2
    assert report.chunks_indexed == 5
    assert len(store._records) == 5


def test_index_all_deletes_before_upserting_for_idempotent_reindex() -> None:
    store = _FakeVectorStore()
    pipeline = IndexingPipeline(
        paper_source=_FakePaperSource([_paper("paper_001", 1)]),
        embedding_provider=_FakeEmbeddingProvider(),
        vector_store=store,
    )

    pipeline.index_all()

    assert store.deleted_paper_ids == ["paper_001"]
    assert len(store.upsert_calls) == 1


def test_chunks_are_tagged_with_correct_paper_id() -> None:
    store = _FakeVectorStore()
    pipeline = IndexingPipeline(
        paper_source=_FakePaperSource([_paper("paper_a", 1), _paper("paper_b", 1)]),
        embedding_provider=_FakeEmbeddingProvider(),
        vector_store=store,
    )

    pipeline.index_all()

    paper_ids = {r.paper_id for r in store._records.values()}
    assert paper_ids == {"paper_a", "paper_b"}


def test_index_all_with_no_papers_reports_zero() -> None:
    store = _FakeVectorStore()
    pipeline = IndexingPipeline(
        paper_source=_FakePaperSource([]),
        embedding_provider=_FakeEmbeddingProvider(),
        vector_store=store,
    )

    report = pipeline.index_all()

    assert report == (0, 0)
    assert store.upsert_calls == []
