"""Integration tests: real PyMuPDFDocumentParser against real (synthetically built)
PDFs — see conftest.py for how the fixture PDFs are constructed."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.interfaces.document_parser import InvalidDocumentError, ParsingError
from src.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser


@pytest.fixture
def parser() -> PyMuPDFDocumentParser:
    return PyMuPDFDocumentParser()


def test_parses_metadata_text_pages(parser: PyMuPDFDocumentParser, well_formed_pdf: Path) -> None:
    result = parser.parse(well_formed_pdf, paper_id="paper_001")
    paper = result.paper

    assert paper.page_count == 3
    assert paper.metadata_source == "pdf_metadata"
    assert paper.title == "A Great Paper About Things"
    assert [a.name for a in paper.authors] == ["Jane Doe", "John Smith"]
    assert len(paper.pages) == 3
    assert all(p.text_length > 0 for p in paper.pages)
    assert len(paper.text_blocks) > 0
    assert all(1 <= b.page <= 3 for b in paper.text_blocks)


def test_detects_at_least_one_section_heading(
    parser: PyMuPDFDocumentParser, well_formed_pdf: Path
) -> None:
    result = parser.parse(well_formed_pdf, paper_id="paper_001")
    titles = {s.title for s in result.paper.sections}
    assert "1. Introduction" in titles or "2. Method" in titles or "References" in titles


def test_extracts_figure_with_bytes_and_caption(
    parser: PyMuPDFDocumentParser, well_formed_pdf: Path
) -> None:
    result = parser.parse(well_formed_pdf, paper_id="paper_001")
    assert len(result.paper.figures) == 1
    figure = result.paper.figures[0]
    assert figure.page == 1
    assert figure.caption is not None and figure.caption.lower().startswith("figure 1")
    assert result.figure_assets[figure.figure_id]
    assert len(result.figure_assets[figure.figure_id]) > 0


def test_extracts_ruled_table(parser: PyMuPDFDocumentParser, well_formed_pdf: Path) -> None:
    result = parser.parse(well_formed_pdf, paper_id="paper_001")
    assert len(result.paper.tables) == 1
    table = result.paper.tables[0]
    assert table.page == 2
    assert len(table.rows) >= 1


def test_extracts_citations_from_references_section(
    parser: PyMuPDFDocumentParser, well_formed_pdf: Path
) -> None:
    result = parser.parse(well_formed_pdf, paper_id="paper_001")
    citations = result.paper.citations
    assert len(citations) == 2
    assert citations[0].marker == "1"
    assert "Referenced Paper" in citations[0].raw_text
    assert all(c.page == 3 for c in citations)


def test_falls_back_to_heuristic_metadata_when_pdf_metadata_missing(
    parser: PyMuPDFDocumentParser, pdf_without_metadata_or_references: Path
) -> None:
    result = parser.parse(pdf_without_metadata_or_references, paper_id="paper_002")
    paper = result.paper

    assert paper.metadata_source == "heuristic"
    assert paper.title == "An Untitled-Metadata Paper Title"
    assert any("heuristic" in w for w in paper.warnings)


def test_reports_missing_references_without_fabricating(
    parser: PyMuPDFDocumentParser, pdf_without_metadata_or_references: Path
) -> None:
    result = parser.parse(pdf_without_metadata_or_references, paper_id="paper_002")
    assert result.paper.citations == []
    assert any("references section not detected" in w for w in result.paper.warnings)


def test_raises_parsing_error_for_blank_text_pdf(
    parser: PyMuPDFDocumentParser, blank_text_pdf: Path
) -> None:
    with pytest.raises(ParsingError):
        parser.parse(blank_text_pdf, paper_id="paper_blank")


def test_raises_invalid_document_error_for_corrupt_file(
    parser: PyMuPDFDocumentParser, invalid_pdf: Path
) -> None:
    with pytest.raises(InvalidDocumentError):
        parser.parse(invalid_pdf, paper_id="paper_corrupt")


def test_raises_invalid_document_error_for_missing_file(
    parser: PyMuPDFDocumentParser, tmp_path: Path
) -> None:
    with pytest.raises(InvalidDocumentError):
        parser.parse(tmp_path / "does_not_exist.pdf", paper_id="paper_missing")
