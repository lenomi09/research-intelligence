"""PaperSource implementation reading already-ingested papers back from disk
(ADR-013's "manual collection input is itself a trivial PaperSource implementation").
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.domain.interfaces.paper_source import PaperSource
from src.domain.models.paper import Paper
from src.ingestion.persistence import PaperLoadError, load_paper

logger = logging.getLogger(__name__)


class LocalCollectionPaperSource(PaperSource):
    """Discovers papers already ingested under
    ``<processed_root>/<paper_id>/`` (Sprint 1's ``scripts/ingest.py`` output).

    A paper directory that fails to load (per ``load_paper``'s required-file rules)
    is logged and skipped, not raised — mirrors ``IngestionPipeline``'s
    one-bad-document-doesn't-abort-the-batch behavior (NFR-006).
    """

    def __init__(self, processed_root: Path) -> None:
        self._processed_root = processed_root

    def list_papers(self) -> list[Paper]:
        papers: list[Paper] = []
        if not self._processed_root.is_dir():
            return papers

        for paper_dir in sorted(self._processed_root.iterdir()):
            if not paper_dir.is_dir():
                continue
            try:
                papers.append(load_paper(paper_dir))
            except PaperLoadError as exc:
                logger.warning(
                    "stage=discovery paper_dir=%s status=skipped error=%s",
                    paper_dir,
                    exc,
                )
        return papers
