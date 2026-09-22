"""End-to-end integration test: real PyMuPDFDocumentParser + IngestionPipeline
(Sprint 1) feeding real LocalCollectionPaperSource + IndexingPipeline +
RetrievalPipeline with real fastembed + real qdrant-client local mode (Sprint 2),
driving a real UnderstandingPipeline (Sprint 3) — but with a fake, deterministic
LLMProvider, since no real LLM endpoint is available in this environment (see
docs/decisions.md ADR-016). Proves the full evidence-label round trip end to end:
the fake LLM only ever cites labels it actually saw in the real prompt, and the
persisted understanding.json ends up with real chunk_ids that exist in the index.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.domain.interfaces.llm_provider import LLMProvider
from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider
from src.infrastructure.paper_sources.local_collection_source import (
    LocalCollectionPaperSource,
)
from src.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser
from src.infrastructure.vector_stores.qdrant_local_store import QdrantLocalVectorStore
from src.ingestion.pipeline import IngestionPipeline
from src.retrieval.indexing import IndexingPipeline
from src.retrieval.retrieval import RetrievalPipeline
from src.understanding.persistence import load_understanding
from src.understanding.pipeline import UnderstandingPipeline

pytestmark = pytest.mark.integration


class _LabelCitingFakeLLMProvider(LLMProvider):
    """Deterministic stand-in for a real LLM: reads the evidence labels actually
    present in the prompt it's given and cites the first one, proving the labels
    the pipeline resolves back into EvidencePointers are real, not invented."""

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        labels = re.findall(r"\[(E\d+)\]", prompt)
        evidence_labels = [labels[0]] if labels else []
        return json.dumps(
            {
                "research_problem": {
                    "value": "the paper studies things",
                    "evidence_labels": evidence_labels,
                    "determination": "stated",
                }
            }
        )


def test_understanding_persists_with_real_chunk_ids_from_the_index(
    well_formed_pdf: Path, tmp_path: Path
) -> None:
    processed_dir = tmp_path / "processed"
    index_dir = tmp_path / "index"

    ingestion = IngestionPipeline(parser=PyMuPDFDocumentParser(), output_root=processed_dir)
    report = ingestion.ingest(well_formed_pdf)
    assert report.success is True
    paper_id = report.paper_id

    embedder = FastEmbedProvider()
    store = QdrantLocalVectorStore(storage_path=index_dir, dimension=embedder.dimension)
    try:
        source = LocalCollectionPaperSource(processed_root=processed_dir)
        indexing = IndexingPipeline(
            paper_source=source, embedding_provider=embedder, vector_store=store
        )
        index_report = indexing.index_all()
        assert index_report.papers_indexed == 1

        retrieval = RetrievalPipeline(embedding_provider=embedder, vector_store=store)
        understanding_pipeline = UnderstandingPipeline(
            paper_source=source,
            retrieval_pipeline=retrieval,
            llm_provider=_LabelCitingFakeLLMProvider(),
            output_root=processed_dir,
        )
        understand_report = understanding_pipeline.understand_all()

        assert understand_report.papers_processed == 1
        assert understand_report.papers_understood == 1
        assert understand_report.papers_failed == 0

        understanding = load_understanding(processed_dir / paper_id)
        assert understanding.extraction_status == "ok"
        assert understanding.research_problem is not None
        assert understanding.research_problem.text == "the paper studies things"
        assert len(understanding.research_problem.evidence) == 1
        pointer = understanding.research_problem.evidence[0]
        assert pointer.paper_id == paper_id
        assert pointer.page >= 1

        # The evidence pointer's chunk_id must be a real chunk that exists in the
        # index (not something the LLM invented) — confirm by retrieving and
        # checking overlap, before the store is closed below.
        hits = retrieval.retrieve("things", top_k=50, paper_ids=[paper_id])
        assert pointer.chunk_id in {h.chunk_id for h in hits}
    finally:
        store.close()
