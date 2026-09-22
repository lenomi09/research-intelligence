"""Ingestion orchestration (architecture.md §3 "Ingestion", §4.1 pipeline diagram).

Wires the pipeline stages together: DocumentParser (interface) → asset extraction →
validation → persistence. This module depends only on the ``DocumentParser``
interface, never on a concrete parser — the concrete implementation is injected by
the caller (see scripts/ingest.py), per NFR-009/ADR-002-style provider
replaceability.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.domain.interfaces.document_parser import (
    DocumentParser,
    InvalidDocumentError,
    ParsingError,
)
from src.ingestion.assets import persist_figure_assets
from src.ingestion.persistence import persist_paper
from src.ingestion.report import IngestionReport
from src.ingestion.validation import build_failure_report, build_report

logger = logging.getLogger(__name__)

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def derive_paper_id(pdf_path: Path) -> str:
    """Derive a filesystem- and JSON-safe paper id from a PDF's filename stem."""
    stem = pdf_path.stem.strip() or "paper"
    return _SAFE_ID_RE.sub("_", stem).strip("_") or "paper"


class IngestionPipeline:
    """Ingests one PDF at a time into ``output_root``, returning an IngestionReport.

    A failure in a *required* stage (the document can't be opened, or produces no
    extractable text at all) is caught here and turned into a failed
    ``IngestionReport`` rather than propagating — so a batch run (see scripts/ingest.py)
    can process the rest of a corpus even when one document is unusable (NFR-006:
    surface failures explicitly, don't let one bad file crash the whole run).
    """

    def __init__(self, parser: DocumentParser, output_root: Path) -> None:
        self._parser = parser
        self._output_root = output_root

    def ingest(self, pdf_path: Path, paper_id: str | None = None) -> IngestionReport:
        paper_id = paper_id or derive_paper_id(pdf_path)
        logger.info("stage=ingest paper_id=%s source=%s status=start", paper_id, pdf_path)

        try:
            paper, figure_assets = self._parser.parse(pdf_path, paper_id)
        except InvalidDocumentError as exc:
            logger.error(
                "stage=parsing paper_id=%s source=%s status=invalid_document error=%s",
                paper_id, pdf_path, exc,
            )
            return build_failure_report(paper_id, str(pdf_path), str(exc))
        except ParsingError as exc:
            logger.error(
                "stage=parsing paper_id=%s source=%s status=parsing_failed error=%s",
                paper_id, pdf_path, exc,
            )
            return build_failure_report(paper_id, str(pdf_path), str(exc))

        paper_dir = self._output_root / paper_id
        asset_warnings = persist_figure_assets(paper, figure_assets, paper_dir)

        report = build_report(paper, paper.warnings, asset_warnings)
        persist_paper(paper, report, self._output_root)

        logger.info(
            "stage=ingest paper_id=%s status=done pages=%s figures=%s tables=%s "
            "citations=%s warnings=%s errors=%s",
            paper_id, report.page_count, report.figure_count, report.table_count,
            report.citation_count, report.warning_count, report.error_count,
        )
        return report
