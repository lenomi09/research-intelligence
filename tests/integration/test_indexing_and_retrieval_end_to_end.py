"""End-to-end integration test: real PyMuPDFDocumentParser + IngestionPipeline
(Sprint 1) feeding real LocalCollectionPaperSource + IndexingPipeline +
RetrievalPipeline, with real fastembed + real qdrant-client local mode (Sprint 2).

This is the concrete proof of Sprint 2's Definition of Done: "For a small manually
curated question set, the system returns retrieved evidence with page citations
across the full collection" (docs/implementation-plan.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider
from src.infrastructure.paper_sources.local_collection_source import (
    LocalCollectionPaperSource,
)
from src.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser
from src.infrastructure.vector_stores.qdrant_local_store import QdrantLocalVectorStore
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.indexing import IndexingPipeline
from src.retrieval.retrieval import RetrievalPipeline

pytestmark = pytest.mark.integration


def test_question_retrieves_evidence_from_the_correct_paper(
    two_topically_distinct_pdfs: list[Path], tmp_path: Path
) -> None:
    processed_dir = tmp_path / "processed"
    index_dir = tmp_path / "index"

    ingestion = IngestionPipeline(parser=PyMuPDFDocumentParser(), output_root=processed_dir)
    for pdf_path in two_topically_distinct_pdfs:
        report = ingestion.ingest(pdf_path)
        assert report.success is True

    embedder = FastEmbedProvider()
    store = QdrantLocalVectorStore(storage_path=index_dir, dimension=embedder.dimension)
    source = LocalCollectionPaperSource(processed_root=processed_dir)
    indexing = IndexingPipeline(
        paper_source=source, embedding_provider=embedder, vector_store=store
    )
    index_report = indexing.index_all()
    assert index_report.papers_indexed == 2

    retrieval = RetrievalPipeline(embedding_provider=embedder, vector_store=store)

    translation_hits = retrieval.retrieve(
        "What dataset was used to evaluate machine translation?", top_k=3
    )
    assert translation_hits[0].paper_id == "paper_transformers"

    robotics_hits = retrieval.retrieve("How was the robot's reward function defined?", top_k=3)
    assert robotics_hits[0].paper_id == "paper_rl_robotics"

    # Paper-scoped filtering: restricting to the wrong paper must not leak the
    # right paper's chunks into the results (the concrete proof of RET-002).
    filtered_hits = retrieval.retrieve(
        "What dataset was used to evaluate machine translation?",
        top_k=3,
        paper_ids=["paper_rl_robotics"],
    )
    assert all(h.paper_id == "paper_rl_robotics" for h in filtered_hits)

    store.close()
