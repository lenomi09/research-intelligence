from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.domain.models.author import Author
from src.domain.models.citation import Citation
from src.domain.models.figure import Figure
from src.domain.models.page import Page
from src.domain.models.table import Table
from src.domain.models.text_block import Section, TextBlock

MetadataSource = Literal["pdf_metadata", "heuristic", "unavailable"]
"""How title/authors were obtained — never claim confidence a source doesn't have.

- ``pdf_metadata``: taken from the PDF's own metadata dictionary (most reliable).
- ``heuristic``: guessed from page-1 layout (largest-font line, following author
  line) because PDF metadata was empty/unusable — see docs/decisions.md ADR-014.
- ``unavailable``: neither source produced a usable value; ``title``/``authors`` are
  left empty rather than fabricated (NFR-006).
"""


class Paper(BaseModel):
    """The top-level ingested-paper aggregate produced by a DocumentParser.

    This is the "Normalized Paper Representation" stage of the ingestion pipeline
    (see architecture.md §4.1): a single, provider-agnostic structure that every
    concrete DocumentParser implementation must produce, regardless of which library
    it used internally. ``warnings`` carries parser-level, non-fatal issues (NFR-006)
    that couldn't be attached to a specific sub-entity.
    """

    paper_id: str
    source_path: str
    title: str | None = None
    authors: list[Author] = Field(default_factory=list)
    abstract: str | None = None
    page_count: int = Field(ge=0)
    metadata_source: MetadataSource

    pages: list[Page] = Field(default_factory=list)
    text_blocks: list[TextBlock] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    figures: list[Figure] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)
