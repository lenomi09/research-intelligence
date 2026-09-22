"""Unit tests for Sprint 1 domain models: construction, defaults, and the field-level
validation that guards against obviously-wrong data (e.g. negative page numbers)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.models import (
    Author,
    BoundingBox,
    Citation,
    Figure,
    Page,
    Paper,
    Section,
    Table,
    TextBlock,
)


def test_page_requires_positive_page_number() -> None:
    Page(page_number=1)  # valid, should not raise
    with pytest.raises(ValidationError):
        Page(page_number=0)


def test_text_block_carries_page_provenance() -> None:
    block = TextBlock(block_id="block_0001", page=3, text="hello", order=0)
    assert block.page == 3
    assert block.bbox is None


def test_figure_starts_without_persisted_path() -> None:
    figure = Figure(figure_id="fig_01", page=2)
    assert figure.image_path is None
    assert figure.caption is None


def test_table_defaults_to_empty_rows() -> None:
    table = Table(table_id="table_01", page=5)
    assert table.rows == []


def test_citation_page_and_marker_are_optional() -> None:
    citation = Citation(citation_id="citation_001", raw_text="A. Author, Some Paper, 2020")
    assert citation.page is None
    assert citation.marker is None


def test_bounding_box_is_immutable() -> None:
    bbox = BoundingBox(x0=0, y0=0, x1=10, y1=10)
    with pytest.raises(ValidationError):
        bbox.x0 = 5  # type: ignore[misc]


def test_paper_round_trips_through_json() -> None:
    paper = Paper(
        paper_id="paper_001",
        source_path="data/papers/raw/paper_001.pdf",
        title="A Great Paper",
        authors=[Author(name="Jane Doe")],
        page_count=2,
        metadata_source="pdf_metadata",
        pages=[Page(page_number=1, text_length=100), Page(page_number=2, text_length=50)],
        text_blocks=[TextBlock(block_id="block_0001", page=1, text="Intro", order=0)],
        sections=[Section(section_id="section_001", title="Introduction", page=1, order=0)],
        figures=[Figure(figure_id="fig_01", page=1)],
        tables=[Table(table_id="table_01", page=2, rows=[["a", "b"]])],
        citations=[Citation(citation_id="citation_001", raw_text="Some reference")],
        warnings=["example warning"],
    )

    reloaded = Paper.model_validate_json(paper.model_dump_json())
    assert reloaded == paper


def test_metadata_source_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        Paper(
            paper_id="paper_001",
            source_path="x.pdf",
            page_count=1,
            metadata_source="made_up",  # type: ignore[arg-type]
        )
