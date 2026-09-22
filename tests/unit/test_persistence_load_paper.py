"""Unit tests for src/ingestion/persistence.py's read side: load_paper."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.models.author import Author
from src.domain.models.citation import Citation
from src.domain.models.figure import Figure
from src.domain.models.page import Page
from src.domain.models.paper import Paper
from src.domain.models.table import Table
from src.domain.models.text_block import Section, TextBlock
from src.ingestion.persistence import PaperLoadError, load_paper, persist_paper
from src.ingestion.report import IngestionReport


def _full_paper() -> Paper:
    return Paper(
        paper_id="paper_001",
        source_path="data/papers/raw/paper_001.pdf",
        title="A Great Paper",
        authors=[Author(name="Jane Doe")],
        abstract="An abstract.",
        page_count=2,
        metadata_source="pdf_metadata",
        pages=[Page(page_number=1, text_length=100), Page(page_number=2, text_length=50)],
        text_blocks=[TextBlock(block_id="block_0001", page=1, text="Intro", order=0)],
        sections=[Section(section_id="section_001", title="Introduction", page=1, order=0)],
        figures=[Figure(figure_id="fig_01", page=1)],
        tables=[Table(table_id="table_01", page=2, rows=[["a", "b"]])],
        citations=[Citation(citation_id="citation_001", raw_text="Some reference", page=2)],
    )


def _report_for(paper: Paper) -> IngestionReport:
    return IngestionReport(
        paper_id=paper.paper_id, source_path=paper.source_path, success=True
    )


def test_load_paper_round_trips_persist_paper(tmp_path: Path) -> None:
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)

    reloaded = load_paper(paper_dir)

    assert reloaded.paper_id == paper.paper_id
    assert reloaded.title == paper.title
    assert reloaded.authors == paper.authors
    assert reloaded.page_count == paper.page_count
    assert reloaded.metadata_source == paper.metadata_source
    assert reloaded.pages == paper.pages
    assert reloaded.text_blocks == paper.text_blocks
    assert reloaded.sections == paper.sections
    assert reloaded.figures == paper.figures
    assert reloaded.tables == paper.tables
    assert reloaded.citations == paper.citations
    assert reloaded.warnings == []


def test_missing_metadata_json_raises_paper_load_error(tmp_path: Path) -> None:
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)
    (paper_dir / "metadata.json").unlink()

    with pytest.raises(PaperLoadError):
        load_paper(paper_dir)


def test_missing_blocks_json_raises_paper_load_error(tmp_path: Path) -> None:
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)
    (paper_dir / "text" / "blocks.json").unlink()

    with pytest.raises(PaperLoadError):
        load_paper(paper_dir)


def test_missing_tables_json_degrades_to_empty_with_warning(tmp_path: Path) -> None:
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)
    (paper_dir / "tables" / "tables.json").unlink()

    reloaded = load_paper(paper_dir)

    assert reloaded.tables == []
    assert reloaded.text_blocks == paper.text_blocks  # unaffected
    assert any("tables" in w for w in reloaded.warnings)


def test_corrupt_figures_json_degrades_to_empty_with_warning(tmp_path: Path) -> None:
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)
    (paper_dir / "figures" / "figures.json").write_text("not valid json{{{", encoding="utf-8")

    reloaded = load_paper(paper_dir)

    assert reloaded.figures == []
    assert any("figures" in w for w in reloaded.warnings)


def test_missing_paper_directory_raises_paper_load_error(tmp_path: Path) -> None:
    with pytest.raises(PaperLoadError):
        load_paper(tmp_path / "does_not_exist")


def test_metadata_json_missing_required_key_raises_paper_load_error_not_key_error(
    tmp_path: Path,
) -> None:
    """Regression test: valid JSON that's missing a required key (e.g. hand-edited
    or from an older schema) must raise PaperLoadError, not a raw KeyError — a raw
    exception here would propagate past LocalCollectionPaperSource's
    `except PaperLoadError` and crash discovery for every other paper too."""
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)
    (paper_dir / "metadata.json").write_text('{"title": "Missing paper_id"}', encoding="utf-8")

    with pytest.raises(PaperLoadError):
        load_paper(paper_dir)


def test_blocks_json_with_wrong_shape_raises_paper_load_error_not_validation_error(
    tmp_path: Path,
) -> None:
    """Regression test: syntactically valid JSON that doesn't match TextBlock's
    shape (e.g. missing 'page') must raise PaperLoadError, not a raw
    pydantic ValidationError."""
    paper = _full_paper()
    paper_dir = persist_paper(paper, _report_for(paper), tmp_path)
    (paper_dir / "text" / "blocks.json").write_text(
        '[{"block_id": "block_0001", "text": "no page field"}]', encoding="utf-8"
    )

    with pytest.raises(PaperLoadError):
        load_paper(paper_dir)
