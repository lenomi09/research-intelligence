"""End-to-end integration test: real parser + real pipeline + real persistence,
including reloading the persisted JSON and re-validating it against the domain
schemas (Sprint 1 Definition of Done item: "output passes schema validation")."""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.models import Citation, Figure, Page, Paper, Section, Table, TextBlock
from src.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.report import IngestionReport


def test_end_to_end_ingestion_produces_schema_valid_persisted_output(
    well_formed_pdf: Path, tmp_path: Path
) -> None:
    output_root = tmp_path / "processed"
    pipeline = IngestionPipeline(parser=PyMuPDFDocumentParser(), output_root=output_root)

    report = pipeline.ingest(well_formed_pdf, paper_id="paper_e2e")

    assert report.success is True
    assert report.error_count == 0

    paper_dir = output_root / "paper_e2e"
    assert paper_dir.is_dir()

    manifest = json.loads((paper_dir / "manifest.json").read_text())
    IngestionReport.model_validate(manifest["report"])  # raises on schema mismatch

    metadata = json.loads((paper_dir / "metadata.json").read_text())
    assert metadata["title"] == "A Great Paper About Things"

    pages = [
        Page.model_validate(p) for p in json.loads((paper_dir / "pages.json").read_text())
    ]
    assert len(pages) == 3

    blocks = [
        TextBlock.model_validate(b)
        for b in json.loads((paper_dir / "text" / "blocks.json").read_text())
    ]
    assert len(blocks) > 0

    sections = [
        Section.model_validate(s)
        for s in json.loads((paper_dir / "text" / "sections.json").read_text())
    ]
    assert len(sections) > 0

    figures = [
        Figure.model_validate(f)
        for f in json.loads((paper_dir / "figures" / "figures.json").read_text())
    ]
    assert len(figures) == 1
    assert figures[0].image_path == "figures/fig_01.png"
    assert (paper_dir / figures[0].image_path).is_file()

    tables = [
        Table.model_validate(t)
        for t in json.loads((paper_dir / "tables" / "tables.json").read_text())
    ]
    assert len(tables) == 1

    citations = [
        Citation.model_validate(c)
        for c in json.loads((paper_dir / "references" / "citations.json").read_text())
    ]
    assert len(citations) == 2

    # Reassembling a Paper from the persisted files must satisfy the same schema
    # as the in-memory object the pipeline produced (round-trip validation).
    reassembled = Paper(
        paper_id=metadata["paper_id"],
        source_path=metadata["source_path"],
        title=metadata["title"],
        authors=metadata["authors"],
        abstract=metadata["abstract"],
        page_count=metadata["page_count"],
        metadata_source=metadata["metadata_source"],
        pages=pages,
        text_blocks=blocks,
        sections=sections,
        figures=figures,
        tables=tables,
        citations=citations,
    )
    assert reassembled.page_count == 3


def test_end_to_end_batch_continues_after_one_bad_file(
    well_formed_pdf: Path, invalid_pdf: Path, tmp_path: Path
) -> None:
    output_root = tmp_path / "processed"
    pipeline = IngestionPipeline(parser=PyMuPDFDocumentParser(), output_root=output_root)

    good_report = pipeline.ingest(well_formed_pdf, paper_id="good")
    bad_report = pipeline.ingest(invalid_pdf, paper_id="bad")

    assert good_report.success is True
    assert bad_report.success is False
    assert (output_root / "good" / "manifest.json").exists()
    assert not (output_root / "bad").exists()
