"""Unit tests for UnderstandingPipeline, using fake PaperSource/RetrievalPipeline
collaborators/LLMProvider (mirrors tests/unit/test_indexing_pipeline.py's pattern)."""

from __future__ import annotations

from pathlib import Path

from src.domain.interfaces.embedding_provider import EmbeddingProvider, Vector
from src.domain.interfaces.llm_provider import LLMError, LLMProvider
from src.domain.interfaces.paper_source import PaperSource
from src.domain.interfaces.vector_store import ScoredChunk, VectorRecord, VectorStore
from src.domain.models.paper import Paper
from src.retrieval.retrieval import RetrievalPipeline
from src.understanding.persistence import load_understanding
from src.understanding.pipeline import UnderstandingPipeline


def _paper(paper_id: str) -> Paper:
    return Paper(
        paper_id=paper_id,
        source_path=f"{paper_id}.pdf",
        title="A Paper",
        abstract="An abstract.",
        page_count=5,
        metadata_source="pdf_metadata",
    )


class _FakePaperSource(PaperSource):
    def __init__(self, papers: list[Paper]) -> None:
        self._papers = papers

    def list_papers(self) -> list[Paper]:
        return self._papers


class _FakeEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 1

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        return [[0.0] for _ in texts]

    def embed_query(self, text: str) -> Vector:
        return [1.0]


class _FakeVectorStore(VectorStore):
    def __init__(self, hits: list[ScoredChunk]) -> None:
        self._hits = hits

    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    def query(
        self, vector: Vector, top_k: int = 5, paper_ids: list[str] | None = None
    ) -> list[ScoredChunk]:
        return self._hits

    def delete_paper(self, paper_id: str) -> None:
        raise NotImplementedError


class _FakeLLMProvider(LLMProvider):
    def __init__(
        self, responses: list[str] | None = None, error: Exception | None = None
    ) -> None:
        self._responses = responses or []
        self._error = error
        self.prompts: list[str] = []

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        self.prompts.append(prompt)
        if self._error is not None:
            raise self._error
        return self._responses.pop(0) if self._responses else "{}"


class _FailThenSucceedFakeLLMProvider(LLMProvider):
    """Errors on the first call, then returns a fixed success response on every
    call after that — proves a later paper can actually succeed after an earlier
    one's LLMError, not just that the loop doesn't stop (see
    test_understand_all_llm_error_on_one_paper_does_not_prevent_next_paper_succeeding)."""

    def __init__(self, success_response: str) -> None:
        self._success_response = success_response
        self._calls = 0

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        self._calls += 1
        if self._calls == 1:
            raise LLMError("boom")
        return self._success_response


def _pipeline(
    papers: list[Paper],
    llm: LLMProvider,
    output_root: Path,
    hits: list[ScoredChunk] | None = None,
) -> UnderstandingPipeline:
    retrieval = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=_FakeVectorStore(hits or [])
    )
    return UnderstandingPipeline(
        paper_source=_FakePaperSource(papers),
        retrieval_pipeline=retrieval,
        llm_provider=llm,
        output_root=output_root,
    )


def test_understand_all_calls_llm_once_per_paper(tmp_path: Path) -> None:
    papers = [_paper("p1"), _paper("p2")]
    llm = _FakeLLMProvider(responses=["{}", "{}"])

    _pipeline(papers, llm, tmp_path).understand_all()

    assert len(llm.prompts) == 2


def test_understand_all_persists_understanding_per_paper(tmp_path: Path) -> None:
    papers = [_paper("p1")]
    hits = [ScoredChunk(chunk_id="c1", paper_id="p1", page=1, text="evidence", score=0.9)]
    llm = _FakeLLMProvider(
        responses=[
            '{"research_problem": {"value": "solve X", "evidence_labels": ["E1"], '
            '"determination": "stated"}}'
        ]
    )

    _pipeline(papers, llm, tmp_path, hits=hits).understand_all()

    loaded = load_understanding(tmp_path / "p1")
    assert loaded.research_problem is not None
    assert loaded.research_problem.text == "solve X"
    assert loaded.extraction_status == "ok"


def test_understand_all_report_counts_understood_and_processed(tmp_path: Path) -> None:
    papers = [_paper("p1"), _paper("p2")]
    llm = _FakeLLMProvider(responses=["{}", "{}"])

    report = _pipeline(papers, llm, tmp_path).understand_all()

    assert report.papers_processed == 2
    assert report.papers_understood == 2
    assert report.papers_failed == 0


def test_understand_all_llm_error_on_one_paper_does_not_abort_batch(tmp_path: Path) -> None:
    papers = [_paper("p1"), _paper("p2")]
    llm = _FakeLLMProvider(error=LLMError("boom"))

    report = _pipeline(papers, llm, tmp_path).understand_all()

    assert report.papers_processed == 2
    assert report.papers_failed == 2
    assert report.papers_understood == 0
    # A failed LLM call still leaves a persisted, failed-status record — "the call
    # errored" must be distinguishable from "this paper was never processed" by
    # looking at disk state alone, not just this run's in-memory report.
    loaded = load_understanding(tmp_path / "p1")
    assert loaded.extraction_status == "failed"
    assert loaded.warnings


def test_understand_all_llm_error_on_one_paper_does_not_prevent_next_paper_succeeding(
    tmp_path: Path,
) -> None:
    papers = [_paper("p1"), _paper("p2")]
    hits = [ScoredChunk(chunk_id="c1", paper_id="p2", page=1, text="evidence", score=0.9)]
    llm = _FailThenSucceedFakeLLMProvider(
        success_response=(
            '{"research_problem": {"value": "solve X", "evidence_labels": ["E1"], '
            '"determination": "stated"}}'
        )
    )

    report = _pipeline(papers, llm, tmp_path, hits=hits).understand_all()

    assert report.papers_processed == 2
    assert report.papers_failed == 1
    assert report.papers_understood == 1
    assert load_understanding(tmp_path / "p1").extraction_status == "failed"
    loaded_p2 = load_understanding(tmp_path / "p2")
    assert loaded_p2.extraction_status == "ok"
    assert loaded_p2.research_problem is not None
    assert loaded_p2.research_problem.text == "solve X"


def test_understand_all_unparseable_response_counts_as_failed_but_persists(
    tmp_path: Path,
) -> None:
    papers = [_paper("p1")]
    llm = _FakeLLMProvider(responses=["not json"])

    report = _pipeline(papers, llm, tmp_path).understand_all()

    assert report.papers_failed == 1
    assert report.papers_understood == 0
    loaded = load_understanding(tmp_path / "p1")
    assert loaded.extraction_status == "failed"


def test_understand_all_empty_source_returns_zeroed_report(tmp_path: Path) -> None:
    report = _pipeline([], _FakeLLMProvider(), tmp_path).understand_all()

    assert report == (0, 0, 0)
