"""Sprint 2 retrieval evaluation harness (RET-008): computes Recall@K and MRR
against retrieval_eval_set.jsonl.

IMPORTANT — read before trusting these numbers: this runs against a small,
hand-built SYNTHETIC corpus (3 papers, 6 questions), not a real curated collection
of scientific papers. No real papers were available in this environment (same
constraint Sprint 1 operated under — see docs/implementation-plan.md). This test
demonstrates that the evaluation harness itself works and that retrieval behaves
sensibly on unambiguous synthetic text; it is not a validated measurement of
retrieval quality on real papers. See docs/evaluation.md's Retrieval Metrics
section, which this harness implements.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.domain.interfaces.paper_source import PaperSource
from src.domain.models.paper import Paper
from src.domain.models.text_block import TextBlock
from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider
from src.infrastructure.vector_stores.qdrant_local_store import QdrantLocalVectorStore
from src.retrieval.indexing import IndexingPipeline
from src.retrieval.retrieval import RetrievalPipeline

pytestmark = pytest.mark.integration

EVAL_SET_PATH = Path(__file__).parent / "retrieval_eval_set.jsonl"
TOP_K = 3
MRR_SEARCH_DEPTH = 10

# The synthetic corpus retrieval_eval_set.jsonl's questions were written against.
# Each paper covers one topic per page so a question's expected (paper_id, page)
# is unambiguous.
_CORPUS_TEXT: dict[str, list[str]] = {
    "paper_nlp": [
        "Transformers use self-attention mechanisms for natural language processing.",
        "We evaluate our translation model on the WMT14 English-German benchmark dataset.",
    ],
    "paper_cv": [
        "Convolutional neural networks are widely used for image classification tasks.",
        "Our object detection model achieves high accuracy on the COCO benchmark dataset.",
    ],
    "paper_rl": [
        "Reinforcement learning agents learn optimal policies through trial and error.",
        "We train our robotic control policy using proximal policy optimization (PPO).",
    ],
}


class _StaticPaperSource(PaperSource):
    def __init__(self, papers: list[Paper]) -> None:
        self._papers = papers

    def list_papers(self) -> list[Paper]:
        return self._papers


def _build_corpus() -> list[Paper]:
    papers = []
    for paper_id, pages_text in _CORPUS_TEXT.items():
        text_blocks = [
            TextBlock(block_id=f"block_{i:04d}", page=i + 1, text=text, order=0)
            for i, text in enumerate(pages_text)
        ]
        papers.append(
            Paper(
                paper_id=paper_id,
                source_path=f"synthetic/{paper_id}.pdf",
                page_count=len(pages_text),
                metadata_source="unavailable",
                text_blocks=text_blocks,
            )
        )
    return papers


def _load_eval_set() -> list[dict]:
    with EVAL_SET_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


@pytest.fixture(scope="module")
def retrieval_pipeline(tmp_path_factory: pytest.TempPathFactory) -> RetrievalPipeline:
    index_dir = tmp_path_factory.mktemp("eval_index")
    embedder = FastEmbedProvider()
    store = QdrantLocalVectorStore(storage_path=index_dir, dimension=embedder.dimension)
    indexing = IndexingPipeline(
        paper_source=_StaticPaperSource(_build_corpus()),
        embedding_provider=embedder,
        vector_store=store,
    )
    indexing.index_all()
    return RetrievalPipeline(embedding_provider=embedder, vector_store=store)


def test_retrieval_metrics_on_synthetic_eval_set(
    retrieval_pipeline: RetrievalPipeline,
) -> None:
    eval_set = _load_eval_set()
    assert len(eval_set) >= 5, "eval set should have a handful of questions"

    recall_hits = 0
    reciprocal_ranks: list[float] = []

    for item in eval_set:
        results = retrieval_pipeline.retrieve(item["question"], top_k=MRR_SEARCH_DEPTH)
        expected = (item["expected_paper_id"], item["expected_page"])

        rank = next(
            (i for i, r in enumerate(results, start=1) if (r.paper_id, r.page) == expected),
            None,
        )
        if rank is not None and rank <= TOP_K:
            recall_hits += 1
        reciprocal_ranks.append(1.0 / rank if rank is not None else 0.0)

    recall_at_k = recall_hits / len(eval_set)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)

    print(
        f"\n[synthetic eval, not a real corpus] Recall@{TOP_K}={recall_at_k:.2f} "
        f"MRR={mrr:.2f} over {len(eval_set)} questions"
    )

    # Demonstrates the harness computes sensible numbers on unambiguous synthetic
    # text — not a claim about real-paper retrieval quality (see module docstring).
    assert recall_at_k >= 0.8
    assert mrr >= 0.8
