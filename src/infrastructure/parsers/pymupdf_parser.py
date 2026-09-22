"""PyMuPDF-backed implementation of the DocumentParser interface (see ADR-014).

Known limitations, documented rather than hidden (NFR-006):
- Vector-drawn figures (not embedded raster images) are not extracted, only
  raster images embedded as PDF XObjects.
- Table detection uses PyMuPDF's built-in ``find_tables`` heuristic, which relies on
  visible ruling lines/whitespace gaps and misses borderless or unusually laid-out
  tables.
- Section/heading and reference-entry detection are font-size/keyword/pattern
  heuristics, not a layout-aware parse, and may miss or misfire on unconventional
  layouts (e.g. camera-ready single-column templates with subtle heading styling).
- Reading order for multi-column layouts follows PyMuPDF's block order, which is not
  always correct for two-column academic layouts.
- Reference capture runs from the "References"/"Bibliography" heading to the end of
  the document; an "Appendix" section after references is excluded when it is itself
  detected as a heading, but non-heading appendix text before the next heading may be
  mis-captured as citation text.
"""

from __future__ import annotations

import logging
import statistics
from pathlib import Path

import pymupdf

from src.domain.interfaces.document_parser import (
    DocumentParser,
    InvalidDocumentError,
    ParseResult,
    ParsingError,
)
from src.domain.models.author import Author
from src.domain.models.citation import Citation
from src.domain.models.common import BoundingBox
from src.domain.models.figure import Figure
from src.domain.models.page import Page
from src.domain.models.paper import Paper
from src.domain.models.table import Table
from src.domain.models.text_block import Section, TextBlock
from src.infrastructure.parsers.heuristics import (
    TextSpan,
    find_nearby_caption,
    guess_title_and_authors,
    is_figure_caption,
    is_heading_candidate,
    is_references_heading,
    is_table_caption,
    split_author_line,
    split_reference_entries,
)

logger = logging.getLogger(__name__)

_BOLD_FLAG = 1 << 4
_STOP_CAPTURING_HEADINGS = {"appendix", "acknowledgements", "acknowledgments"}


class PyMuPDFDocumentParser(DocumentParser):
    """DocumentParser implementation backed by PyMuPDF. See module docstring for
    documented extraction limitations."""

    def parse(self, pdf_path: Path, paper_id: str) -> ParseResult:
        try:
            doc = pymupdf.open(pdf_path)
        except Exception as exc:  # pymupdf raises varied exception types for bad files
            raise InvalidDocumentError(
                f"could not open '{pdf_path}' as a PDF: {exc}"
            ) from exc

        try:
            if doc.page_count == 0:
                raise InvalidDocumentError(f"'{pdf_path}' has zero pages")
            return self._parse_open_document(doc, pdf_path, paper_id)
        finally:
            doc.close()

    # -- pipeline stages ----------------------------------------------------

    def _parse_open_document(
        self, doc: pymupdf.Document, pdf_path: Path, paper_id: str
    ) -> ParseResult:
        warnings: list[str] = []

        pages: list[Page] = []
        text_blocks: list[TextBlock] = []
        sections: list[Section] = []
        figures: list[Figure] = []
        figure_assets: dict[str, bytes] = {}
        tables: list[Table] = []

        block_counter = 0
        fig_counter = 0
        table_counter = 0
        total_text_length = 0
        find_tables_warned = False

        first_page_lines: list[tuple[str, float]] = []
        references_lines: list[tuple[str, int]] = []
        capturing_references = False

        for page_index in range(doc.page_count):
            page = doc[page_index]
            page_number = page_index + 1
            page_dict = page.get_text("dict")

            line_records = _extract_line_records(page_dict)
            page_text_length = sum(len(text) for text, _, _ in line_records)
            total_text_length += page_text_length

            pages.append(
                Page(
                    page_number=page_number,
                    width=page.rect.width,
                    height=page.rect.height,
                    text_length=page_text_length,
                    has_extraction_issue=page_text_length == 0,
                )
            )
            if page_text_length == 0:
                warnings.append(
                    f"page {page_number}: no extractable text "
                    "(possibly scanned/image-only or a blank page)"
                )

            if page_number == 1:
                first_page_lines = [
                    (text, max((s.size for s in spans), default=0.0))
                    for text, _, spans in line_records
                ]

            median_size = (
                statistics.median(s.size for _, _, spans in line_records for s in spans)
                if any(spans for _, _, spans in line_records)
                else 0.0
            )

            block_counter = _append_text_blocks(
                page_dict, page_number, block_counter, text_blocks
            )

            for line_text, _line_bbox, spans in line_records:
                stripped = line_text.strip()
                heading = is_heading_candidate(line_text, spans, median_size)

                if is_references_heading(stripped):
                    capturing_references = True
                    continue

                if capturing_references and heading and stripped.lower().rstrip(".:") in _STOP_CAPTURING_HEADINGS:
                    capturing_references = False

                if heading:
                    sections.append(
                        Section(
                            section_id=f"section_{len(sections) + 1:03d}",
                            title=stripped,
                            page=page_number,
                            order=len(sections) + 1,
                        )
                    )

                if capturing_references:
                    references_lines.append((line_text, page_number))

            fig_counter = self._extract_figures(
                doc, page, page_number, line_records, fig_counter,
                figures, figure_assets, warnings, paper_id,
            )

            table_counter, find_tables_warned = self._extract_tables(
                page, page_number, line_records, table_counter,
                tables, warnings, paper_id, find_tables_warned,
            )

        if total_text_length == 0:
            raise ParsingError(
                f"'{pdf_path}' produced no extractable text on any page — likely a "
                "scanned/image-only PDF; OCR is out of scope for Sprint 1 (see FR-109)"
            )

        title, authors, metadata_source, abstract = self._extract_metadata(
            doc, first_page_lines, warnings
        )
        citations, citation_warnings = self._extract_citations(references_lines)
        warnings.extend(citation_warnings)

        paper = Paper(
            paper_id=paper_id,
            source_path=str(pdf_path),
            title=title,
            authors=authors,
            abstract=abstract,
            page_count=doc.page_count,
            metadata_source=metadata_source,
            pages=pages,
            text_blocks=text_blocks,
            sections=sections,
            figures=figures,
            tables=tables,
            citations=citations,
            warnings=warnings,
        )
        return ParseResult(paper=paper, figure_assets=figure_assets)

    def _extract_figures(
        self,
        doc: pymupdf.Document,
        page: pymupdf.Page,
        page_number: int,
        line_records: list[tuple[str, tuple[float, float, float, float], list[TextSpan]]],
        fig_counter: int,
        figures: list[Figure],
        figure_assets: dict[str, bytes],
        warnings: list[str],
        paper_id: str,
    ) -> int:
        caption_lines = [(t, b) for t, b, _ in line_records]
        for xref, *_ in page.get_images(full=True):
            try:
                img_info = doc.extract_image(xref)
                img_bytes = img_info["image"]
                img_ext = img_info.get("ext", "png")
                rects = page.get_image_rects(xref)
                img_bbox = rects[0] if rects else None

                fig_counter += 1
                figure_id = f"fig_{fig_counter:02d}"
                caption = None
                if img_bbox is not None:
                    target = (img_bbox.x0, img_bbox.y0, img_bbox.x1, img_bbox.y1)
                    caption = find_nearby_caption(target, caption_lines, is_figure_caption)

                figures.append(
                    Figure(
                        figure_id=figure_id,
                        page=page_number,
                        caption=caption,
                        image_ext=img_ext,
                        bbox=(
                            BoundingBox(
                                x0=img_bbox.x0, y0=img_bbox.y0, x1=img_bbox.x1, y1=img_bbox.y1
                            )
                            if img_bbox is not None
                            else None
                        ),
                    )
                )
                figure_assets[figure_id] = img_bytes
            except Exception as exc:  # optional extraction — log and continue (NFR-006)
                warnings.append(
                    f"page {page_number}: figure extraction failed for image "
                    f"xref={xref}: {exc}"
                )
                logger.warning(
                    "stage=figures paper_id=%s page=%s xref=%s error=%s",
                    paper_id, page_number, xref, exc,
                )
        return fig_counter

    def _extract_tables(
        self,
        page: pymupdf.Page,
        page_number: int,
        line_records: list[tuple[str, tuple[float, float, float, float], list[TextSpan]]],
        table_counter: int,
        tables: list[Table],
        warnings: list[str],
        paper_id: str,
        already_warned_unsupported: bool,
    ) -> tuple[int, bool]:
        caption_lines = [(t, b) for t, b, _ in line_records]

        if not hasattr(page, "find_tables"):
            if not already_warned_unsupported:
                warnings.append(
                    "table extraction unsupported by the installed PyMuPDF version "
                    "(no find_tables); no tables will be extracted for this document"
                )
            return table_counter, True

        try:
            table_finder = page.find_tables()
        except Exception as exc:  # table detection itself failed for this page
            warnings.append(f"page {page_number}: table detection failed: {exc}")
            logger.warning(
                "stage=tables paper_id=%s page=%s error=%s", paper_id, page_number, exc
            )
            return table_counter, already_warned_unsupported

        for found_table in table_finder.tables:
            try:
                rows = found_table.extract()
                table_counter += 1
                table_id = f"table_{table_counter:02d}"
                bbox = found_table.bbox
                caption = find_nearby_caption(tuple(bbox), caption_lines, is_table_caption)
                tables.append(
                    Table(
                        table_id=table_id,
                        page=page_number,
                        caption=caption,
                        rows=[list(row) for row in rows],
                        bbox=BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
                    )
                )
            except Exception as exc:  # optional extraction — log and continue (NFR-006)
                warnings.append(
                    f"page {page_number}: failed to extract a detected table: {exc}"
                )
                logger.warning(
                    "stage=tables paper_id=%s page=%s error=%s", paper_id, page_number, exc
                )
        return table_counter, already_warned_unsupported

    def _extract_metadata(
        self,
        doc: pymupdf.Document,
        first_page_lines: list[tuple[str, float]],
        warnings: list[str],
    ) -> tuple[str | None, list[Author], str, str | None]:
        raw_meta = doc.metadata or {}
        pdf_title = (raw_meta.get("title") or "").strip()
        pdf_author = (raw_meta.get("author") or "").strip()

        if pdf_title and not _looks_like_placeholder_title(pdf_title):
            authors = [
                Author(name=n, raw=pdf_author) for n in split_author_line(pdf_author)
            ]
            return pdf_title, authors, "pdf_metadata", None

        guessed_title, guessed_author_line = guess_title_and_authors(first_page_lines)
        if guessed_title:
            authors = (
                [
                    Author(name=n, raw=guessed_author_line)
                    for n in split_author_line(guessed_author_line)
                ]
                if guessed_author_line
                else []
            )
            warnings.append(
                "title/authors were not available in PDF metadata; used a page-1 "
                "layout heuristic instead (metadata_source=heuristic)"
            )
            return guessed_title, authors, "heuristic", None

        warnings.append(
            "could not determine title/authors from PDF metadata or page-1 layout"
        )
        return None, [], "unavailable", None

    def _extract_citations(
        self, references_lines: list[tuple[str, int]]
    ) -> tuple[list[Citation], list[str]]:
        if not references_lines:
            return [], ["references section not detected; no citations extracted"]

        references_page = references_lines[0][1]
        blob = "\n".join(text for text, _ in references_lines)
        entries = split_reference_entries(blob)

        warnings: list[str] = []
        if len(entries) == 1:
            warnings.append(
                "references section found but could not be confidently split into "
                "individual entries; stored as a single citation"
            )

        citations = [
            Citation(
                citation_id=f"citation_{i + 1:03d}",
                raw_text=raw_text,
                page=references_page,
                marker=marker,
            )
            for i, (raw_text, marker) in enumerate(entries)
        ]
        return citations, warnings


def _extract_line_records(
    page_dict: dict,
) -> list[tuple[str, tuple[float, float, float, float], list[TextSpan]]]:
    records: list[tuple[str, tuple[float, float, float, float], list[TextSpan]]] = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [
                TextSpan(
                    text=s.get("text", ""),
                    size=s.get("size", 0.0),
                    bold=bool(s.get("flags", 0) & _BOLD_FLAG),
                )
                for s in line.get("spans", [])
            ]
            line_text = "".join(s.text for s in spans)
            if not line_text.strip():
                continue
            bbox = tuple(line.get("bbox", (0.0, 0.0, 0.0, 0.0)))
            records.append((line_text, bbox, spans))
    return records


def _append_text_blocks(
    page_dict: dict,
    page_number: int,
    block_counter: int,
    text_blocks: list[TextBlock],
) -> int:
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        block_lines = [
            "".join(s.get("text", "") for s in line.get("spans", []))
            for line in block.get("lines", [])
        ]
        block_text = " ".join(t for t in block_lines if t.strip()).strip()
        if not block_text:
            continue
        bbox = block.get("bbox", (0.0, 0.0, 0.0, 0.0))
        block_counter += 1
        text_blocks.append(
            TextBlock(
                block_id=f"block_{block_counter:04d}",
                page=page_number,
                text=block_text,
                order=block_counter,
                bbox=BoundingBox(x0=bbox[0], y0=bbox[1], x1=bbox[2], y1=bbox[3]),
            )
        )
    return block_counter


def _looks_like_placeholder_title(title: str) -> bool:
    lowered = title.lower().strip()
    if lowered.endswith(".pdf") or lowered.endswith(".tex"):
        return True
    return lowered in {"untitled", "untitled document", "microsoft word - document1"}
