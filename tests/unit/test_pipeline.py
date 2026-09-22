"""Unit tests for IngestionPipeline orchestration, using a fake DocumentParser so
these don't depend on real PDF parsing (that's covered by the integration tests)."""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.interfaces.document_parser import (
    DocumentParser,
    InvalidDocumentError,
    ParseResult,
    ParsingError,
)
from src.domain.models import Figure, Page, Paper, TextBlock
from src.ingestion.pipeline import IngestionPipeline, derive_paper_id


class _FakeParser(DocumentParser):
    def __init__(self, result: ParseResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error

    def parse(self, pdf_path: Path, paper_id: str) -> ParseResult:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _make_valid_result(paper_id: str = "paper_001") -> ParseResult:
    paper = Paper(
        paper_id=paper_id,
        source_path="irrelevant.pdf",
        title="Test Paper",
        page_count=1,
        metadata_source="pdf_metadata",
        pages=[Page(page_number=1, text_length=42)],
        text_blocks=[TextBlock(block_id="block_0001", page=1, text="hello", order=0)],
        figures=[Figure(figure_id="fig_01", page=1, image_ext="png")],
    )
    return ParseResult(paper=paper, figure_assets={"fig_01": b"\x89PNG-fake-bytes"})


def test_derive_paper_id_sanitizes_unsafe_characters() -> None:
    assert derive_paper_id(Path("My Paper: Draft (v2).pdf")) == "My_Paper_Draft_v2"


def test_ingest_returns_failure_report_on_invalid_document(tmp_path: Path) -> None:
    parser = _FakeParser(error=InvalidDocumentError("not a real PDF"))
    pipeline = IngestionPipeline(parser=parser, output_root=tmp_path)

    report = pipeline.ingest(tmp_path / "bad.pdf")

    assert report.success is False
    assert report.error_count == 1
    assert "not a real PDF" in report.issues[0].message
    # A required-stage failure must not crash the pipeline or write partial output.
    assert not (tmp_path / report.paper_id).exists()


def test_ingest_returns_failure_report_on_parsing_error(tmp_path: Path) -> None:
    parser = _FakeParser(error=ParsingError("no extractable text found"))
    pipeline = IngestionPipeline(parser=parser, output_root=tmp_path)

    report = pipeline.ingest(tmp_path / "scanned.pdf")

    assert report.success is False
    assert "no extractable text" in report.issues[0].message


def test_ingest_persists_output_on_success(tmp_path: Path) -> None:
    result = _make_valid_result()
    parser = _FakeParser(result=result)
    pipeline = IngestionPipeline(parser=parser, output_root=tmp_path)

    report = pipeline.ingest(tmp_path / "good.pdf", paper_id="paper_001")

    assert report.success is True
    assert report.page_count == 1
    assert report.text_block_count == 1
    assert report.figure_count == 1

    paper_dir = tmp_path / "paper_001"
    manifest = json.loads((paper_dir / "manifest.json").read_text())
    assert manifest["report"]["paper_id"] == "paper_001"

    metadata = json.loads((paper_dir / "metadata.json").read_text())
    assert metadata["title"] == "Test Paper"

    figure_bytes = (paper_dir / "figures" / "fig_01.png").read_bytes()
    assert figure_bytes == b"\x89PNG-fake-bytes"

    figures_json = json.loads((paper_dir / "figures" / "figures.json").read_text())
    assert figures_json[0]["image_path"] == "figures/fig_01.png"


def test_ingest_flags_out_of_range_page_reference(tmp_path: Path) -> None:
    paper = Paper(
        paper_id="paper_002",
        source_path="irrelevant.pdf",
        page_count=1,
        metadata_source="unavailable",
        text_blocks=[TextBlock(block_id="block_0001", page=99, text="oops", order=0)],
    )
    parser = _FakeParser(result=ParseResult(paper=paper, figure_assets={}))
    pipeline = IngestionPipeline(parser=parser, output_root=tmp_path)

    report = pipeline.ingest(tmp_path / "weird.pdf", paper_id="paper_002")

    assert report.success is True  # required stage still succeeded
    assert report.error_count >= 1
    assert any("out-of-range page" in issue.message for issue in report.issues)


def test_ingest_does_not_crash_when_figure_bytes_missing(tmp_path: Path) -> None:
    paper = Paper(
        paper_id="paper_003",
        source_path="irrelevant.pdf",
        page_count=1,
        metadata_source="unavailable",
        figures=[Figure(figure_id="fig_missing", page=1, image_ext="png")],
    )
    parser = _FakeParser(result=ParseResult(paper=paper, figure_assets={}))
    pipeline = IngestionPipeline(parser=parser, output_root=tmp_path)

    report = pipeline.ingest(tmp_path / "weird2.pdf", paper_id="paper_003")

    assert report.success is True
    assert any("no image bytes were captured" in issue.message for issue in report.issues)
