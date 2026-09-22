"""Sprint 3 understanding evaluation harness (UND-006): computes field-level
substring-match accuracy and evidence-page accuracy against
understanding_eval_set.jsonl.

IMPORTANT — read before trusting these numbers: this runs against a small,
hand-built SYNTHETIC corpus (2 papers, 10 eval items) and a deterministic FAKE
LLMProvider that returns known-correct JSON — not a real LLM (none was available in
this environment; see docs/decisions.md ADR-016). This test demonstrates that the
evaluation harness mechanics work (it can compute these metrics end to end through
real chunking/embedding/retrieval and the real prompting/parsing pipeline); it is not
a validated measurement of real extraction quality against a real LLM or real papers.
See docs/evaluation.md's Extraction Metrics section, which this harness implements.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src.domain.interfaces.llm_provider import LLMProvider
from src.domain.interfaces.paper_source import PaperSource
from src.domain.models.paper import Paper
from src.domain.models.text_block import TextBlock
from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider
from src.infrastructure.vector_stores.qdrant_local_store import QdrantLocalVectorStore
from src.retrieval.indexing import IndexingPipeline
from src.retrieval.retrieval import RetrievalPipeline
from src.understanding.models import PaperUnderstanding
from src.understanding.pipeline import UnderstandingPipeline

pytestmark = pytest.mark.integration

EVAL_SET_PATH = Path(__file__).parent / "understanding_eval_set.jsonl"

# The synthetic corpus understanding_eval_set.jsonl's questions were written
# against — one page per paper so every field's expected page is unambiguous.
_CORPUS_TEXT: dict[str, str] = {
    "paper_nlp": (
        "We address the problem of improving machine translation quality between "
        "distant language pairs. We propose a Transformer-based model using "
        "self-attention. We evaluate on the WMT14 English-German dataset and report "
        "BLEU scores. A key limitation is that we only evaluated on one language pair."
    ),
    "paper_rl": (
        "We address the problem of learning precise robotic arm manipulation "
        "policies from raw sensor input. We propose an approach using PPO "
        "(Proximal Policy Optimization). We evaluate on a simulated grasping "
        "benchmark and report task success rate. A limitation of this work is that "
        "it was not tested on a physical robot."
    ),
}

# Known-correct extraction the fake LLM returns for each paper — stands in for what
# a real LLM would ideally produce, so the harness has something to score against.
_EXPECTED_EXTRACTION: dict[str, dict] = {
    "paper_nlp": {
        "research_problem": (
            "improving machine translation quality between distant language pairs"
        ),
        "methods": ["Transformer-based model using self-attention"],
        "datasets": ["WMT14 English-German dataset"],
        "metrics": ["BLEU"],
        "limitations": ["only evaluated on one language pair"],
    },
    "paper_rl": {
        "research_problem": "learning precise robotic arm manipulation policies",
        "methods": ["PPO (Proximal Policy Optimization)"],
        "datasets": ["simulated grasping benchmark"],
        "metrics": ["task success rate"],
        "limitations": ["not tested on a physical robot"],
    },
}


class _StaticPaperSource(PaperSource):
    def __init__(self, papers: list[Paper]) -> None:
        self._papers = papers

    def list_papers(self) -> list[Paper]:
        return self._papers


def _build_corpus() -> list[Paper]:
    papers = []
    for paper_id, text in _CORPUS_TEXT.items():
        block = TextBlock(block_id="block_0000", page=1, text=text, order=0)
        papers.append(
            Paper(
                paper_id=paper_id,
                source_path=f"synthetic/{paper_id}.pdf",
                title=paper_id,
                page_count=1,
                metadata_source="unavailable",
                text_blocks=[block],
            )
        )
    return papers


def _load_eval_set() -> list[dict]:
    with EVAL_SET_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class _KnownCorrectFakeLLMProvider(LLMProvider):
    """Returns hand-authored, known-correct JSON for each paper, citing whichever
    real evidence labels the prompt actually contains — every chunk in this corpus
    is on page 1, so any label found is a page-1 label (see module docstring)."""

    def __init__(self, expected: dict[str, dict]) -> None:
        self._expected = expected
        self.paper_ids_seen: list[str] = []

    def complete(self, prompt: str, *, max_tokens: int | None = None) -> str:
        paper_id = next(pid for pid in self._expected if pid in prompt)
        self.paper_ids_seen.append(paper_id)
        expected = self._expected[paper_id]
        labels = re.findall(r"\[(E\d+)\]", prompt)
        evidence_labels = labels[:1]

        def entry(text_key: str, value: str) -> dict:
            return {
                text_key: value,
                "evidence_labels": evidence_labels,
                "determination": "stated",
            }

        return json.dumps(
            {
                "research_problem": entry("value", expected["research_problem"]),
                "methods": [entry("name", name) for name in expected["methods"]],
                "datasets": [entry("name", name) for name in expected["datasets"]],
                "metrics": [entry("name", name) for name in expected["metrics"]],
                "limitations": [entry("value", text) for text in expected["limitations"]],
            }
        )


def _field_entries(understanding: PaperUnderstanding, field: str) -> list[tuple[str, list]]:
    if field == "research_problem":
        if understanding.research_problem is None:
            return []
        return [(understanding.research_problem.text, understanding.research_problem.evidence)]
    if field == "methods":
        return [(m.name, m.evidence) for m in understanding.methods]
    if field == "datasets":
        return [(d.name, d.evidence) for d in understanding.datasets]
    if field == "metrics":
        return [(m.name, m.evidence) for m in understanding.metrics]
    if field == "limitations":
        return [(s.text, s.evidence) for s in understanding.limitations]
    raise ValueError(f"unknown field: {field}")


@pytest.fixture(scope="module")
def understandings(tmp_path_factory: pytest.TempPathFactory) -> dict[str, PaperUnderstanding]:
    processed_dir = tmp_path_factory.mktemp("eval_processed")
    index_dir = tmp_path_factory.mktemp("eval_index")

    embedder = FastEmbedProvider()
    store = QdrantLocalVectorStore(storage_path=index_dir, dimension=embedder.dimension)
    try:
        source = _StaticPaperSource(_build_corpus())
        IndexingPipeline(
            paper_source=source, embedding_provider=embedder, vector_store=store
        ).index_all()

        retrieval = RetrievalPipeline(embedding_provider=embedder, vector_store=store)
        pipeline = UnderstandingPipeline(
            paper_source=source,
            retrieval_pipeline=retrieval,
            llm_provider=_KnownCorrectFakeLLMProvider(_EXPECTED_EXTRACTION),
            output_root=processed_dir,
        )
        pipeline.understand_all()

        from src.understanding.persistence import load_understanding

        return {
            paper_id: load_understanding(processed_dir / paper_id) for paper_id in _CORPUS_TEXT
        }
    finally:
        store.close()


def test_understanding_metrics_on_synthetic_eval_set(
    understandings: dict[str, PaperUnderstanding],
) -> None:
    eval_set = _load_eval_set()
    assert len(eval_set) >= 5, "eval set should have a handful of items"

    field_hits = 0
    evidence_page_hits = 0

    for item in eval_set:
        understanding = understandings[item["paper_id"]]
        entries = _field_entries(understanding, item["field"])

        matched_evidence: list = []
        field_matched = False
        for text, evidence in entries:
            if item["expected_substring"] in text:
                field_matched = True
                matched_evidence = evidence
                break

        if field_matched:
            field_hits += 1
            if any(p.page == item["expected_page"] for p in matched_evidence):
                evidence_page_hits += 1

    field_accuracy = field_hits / len(eval_set)
    evidence_page_accuracy = evidence_page_hits / len(eval_set)

    print(
        f"\n[synthetic eval, fake LLM, not real quality] field_accuracy="
        f"{field_accuracy:.2f} evidence_page_accuracy={evidence_page_accuracy:.2f} "
        f"over {len(eval_set)} items"
    )

    # Demonstrates the harness computes sensible numbers on unambiguous synthetic
    # text with a known-correct fake LLM — not a claim about real extraction
    # quality against a real LLM or real papers (see module docstring).
    assert field_accuracy >= 0.8
    assert evidence_page_accuracy >= 0.8
