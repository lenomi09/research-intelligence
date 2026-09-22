"""The DocumentParser interface (see architecture.md §2.3/§8, ADR-014).

Every concrete parser (Sprint 1: PyMuPDF; a second implementation may be added later
per ING-010 to validate swappability, per NFR-009) implements this interface and
nothing outside src/infrastructure/parsers may import a parsing library directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import NamedTuple

from src.domain.models.paper import Paper


class ParseResult(NamedTuple):
    """A parser's output: the normalized ``Paper`` plus not-yet-persisted figure bytes.

    Figure image bytes are kept out of the ``Paper`` model itself (see Figure's
    docstring) so parsing stays a pure, disk-write-free operation — persistence is the
    ingestion pipeline's job (architecture.md's "Asset Extraction" pipeline stage), not
    the parser's.
    """

    paper: Paper
    figure_assets: dict[str, bytes]
    """Maps ``Figure.figure_id`` to the figure's raw encoded image bytes."""


class ParsingError(Exception):
    """Raised when a required extraction stage fails for a document.

    A required failure aborts ingestion for that document (the document cannot be
    ingested at all) — this is distinct from an *optional* extraction failure (e.g. one
    figure's caption not found), which is recorded as a warning on ``Paper.warnings``
    instead of raised (see docs/development-guidelines.md Error Handling, NFR-006).
    """


class InvalidDocumentError(ParsingError):
    """Raised when the input file cannot be opened as a PDF at all (corrupt/invalid)."""


class DocumentParser(ABC):
    """Parses a PDF file into a normalized, provider-agnostic ``Paper`` representation."""

    @abstractmethod
    def parse(self, pdf_path: Path, paper_id: str) -> ParseResult:
        """Parse ``pdf_path`` into a ``ParseResult``.

        Raises:
            InvalidDocumentError: the file could not be opened as a PDF at all.
            ParsingError: a required extraction stage (text) failed for a document
                that did open successfully.
        """
        raise NotImplementedError
