"""Understanding orchestration (architecture.md §3/§4.3): for every paper a
PaperSource provides, retrieves labeled evidence, asks the LLMProvider once for a
structured extraction, and persists the result — the Understanding-side analog of
IndexingPipeline (src/retrieval/indexing.py). Depends only on domain interfaces;
concrete implementations are injected by the caller (see scripts/understand.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

from src.domain.interfaces.llm_provider import LLMError, LLMProvider
from src.domain.interfaces.paper_source import PaperSource
from src.retrieval.retrieval import RetrievalPipeline
from src.understanding.models import PaperUnderstanding
from src.understanding.persistence import persist_understanding
from src.understanding.prompting import (
    DEFAULT_MAX_EVIDENCE_CHARS,
    DEFAULT_TOP_K_PER_FIELD,
    build_extraction_prompt,
    build_paper_understanding,
    collect_labeled_evidence,
    parse_extraction_response,
)

logger = logging.getLogger(__name__)


class UnderstandingReport(NamedTuple):
    papers_processed: int
    papers_understood: int
    papers_failed: int


class UnderstandingPipeline:
    """Extracts and persists a PaperUnderstanding for every paper a PaperSource
    provides. One LLMProvider.complete() call per paper (not per field, ADR-006's
    cost-control choice). A single paper's LLMError never aborts the batch — mirrors
    LocalCollectionPaperSource catching PaperLoadError per directory (NFR-006).
    """

    def __init__(
        self,
        paper_source: PaperSource,
        retrieval_pipeline: RetrievalPipeline,
        llm_provider: LLMProvider,
        output_root: Path,
        top_k_per_field: int = DEFAULT_TOP_K_PER_FIELD,
        max_evidence_chars: int = DEFAULT_MAX_EVIDENCE_CHARS,
    ) -> None:
        self._source = paper_source
        self._retrieval = retrieval_pipeline
        self._llm = llm_provider
        self._output_root = output_root
        self._top_k_per_field = top_k_per_field
        self._max_evidence_chars = max_evidence_chars

    def understand_all(self) -> UnderstandingReport:
        papers = self._source.list_papers()
        understood = 0
        failed = 0

        for paper in papers:
            labeled_evidence = collect_labeled_evidence(
                paper.paper_id,
                self._retrieval,
                self._top_k_per_field,
                self._max_evidence_chars,
            )
            prompt = build_extraction_prompt(paper, labeled_evidence)

            try:
                raw_response = self._llm.complete(prompt)
            except LLMError as exc:
                logger.error(
                    "stage=understanding paper_id=%s status=failed error=%s",
                    paper.paper_id,
                    exc,
                )
                # Persist a failed-status record here too (not just on a parse
                # failure below) — otherwise "the LLM call itself errored" is
                # indistinguishable from "this paper was never processed" once you
                # only have the persisted output to look at, contradicting
                # PaperUnderstanding.extraction_status's own documented contract.
                persist_understanding(
                    PaperUnderstanding(
                        paper_id=paper.paper_id,
                        extraction_status="failed",
                        warnings=[f"LLM completion request failed: {exc}"],
                    ),
                    self._output_root,
                )
                failed += 1
                continue

            parsed = parse_extraction_response(raw_response, labeled_evidence, paper.paper_id)
            understanding = build_paper_understanding(paper.paper_id, parsed)
            persist_understanding(understanding, self._output_root)

            if understanding.extraction_status == "failed":
                failed += 1
            else:
                understood += 1
            logger.info(
                "stage=understanding paper_id=%s status=%s",
                paper.paper_id,
                understanding.extraction_status,
            )

        return UnderstandingReport(
            papers_processed=len(papers), papers_understood=understood, papers_failed=failed
        )
