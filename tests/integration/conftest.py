"""Fixtures that build small synthetic PDFs with PyMuPDF itself, so integration
tests don't need any committed binary PDF fixtures (see docs/decisions.md ADR-014
and README.md on why real papers aren't committed to the repo)."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest


def _add_solid_image(page: pymupdf.Page, rect: pymupdf.Rect, rgb: tuple[int, int, int]) -> None:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 40), False)
    pix.set_rect(pix.irect, rgb)
    page.insert_image(rect, pixmap=pix)


@pytest.fixture
def well_formed_pdf(tmp_path: Path) -> Path:
    """A 3-page synthetic paper with metadata, a heading, a figure with a caption,
    a ruled table, and a References section with two numbered entries."""
    doc = pymupdf.open()

    page1 = doc.new_page()
    page1.insert_text((72, 72), "A Great Paper About Things", fontsize=18)
    page1.insert_text((72, 100), "Jane Doe, John Smith", fontsize=11)
    page1.insert_text((72, 130), "Abstract", fontsize=13)
    page1.insert_text(
        (72, 150),
        "This paper studies things and reports results on a benchmark dataset.",
        fontsize=10,
    )
    page1.insert_text((72, 200), "1. Introduction", fontsize=13)
    page1.insert_text(
        (72, 220),
        "Introductory text goes here explaining the motivation for this work.",
        fontsize=10,
    )
    _add_solid_image(page1, pymupdf.Rect(72, 300, 220, 380), (200, 50, 50))
    page1.insert_text((72, 385), "Figure 1: An example plot.", fontsize=9)

    page2 = doc.new_page()
    page2.insert_text((72, 72), "2. Method", fontsize=13)
    page2.insert_text((72, 90), "Table 1: Results on the benchmark.", fontsize=9)
    x0, y0, x1, y1 = 72, 100, 300, 180
    mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
    shape = page2.new_shape()
    shape.draw_rect(pymupdf.Rect(x0, y0, x1, y1))
    shape.draw_line((x0, mid_y), (x1, mid_y))
    shape.draw_line((mid_x, y0), (mid_x, y1))
    shape.finish()
    shape.commit()
    page2.insert_text((x0 + 5, y0 + 15), "Model")
    page2.insert_text((mid_x + 5, y0 + 15), "Accuracy")
    page2.insert_text((x0 + 5, mid_y + 15), "Baseline")
    page2.insert_text((mid_x + 5, mid_y + 15), "0.80")

    page3 = doc.new_page()
    page3.insert_text((72, 72), "References", fontsize=13)
    page3.insert_text(
        (72, 90), "[1] A. Author. A Referenced Paper. Conference, 2020.", fontsize=9
    )
    page3.insert_text(
        (72, 105), "[2] B. Author. Another Referenced Paper. Journal, 2021.", fontsize=9
    )

    doc.set_metadata({"title": "A Great Paper About Things", "author": "Jane Doe, John Smith"})

    pdf_path = tmp_path / "well_formed.pdf"
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def pdf_without_metadata_or_references(tmp_path: Path) -> Path:
    """A 1-page PDF with no PDF-level metadata and no References section, to exercise
    the heuristic-title fallback and the "references not detected" path."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "An Untitled-Metadata Paper Title", fontsize=18)
    page.insert_text((72, 100), "A. Nonymous", fontsize=11)
    page.insert_text(
        (72, 140),
        "Body text with no distinguishing structure and no references section.",
        fontsize=10,
    )
    pdf_path = tmp_path / "no_metadata.pdf"
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def blank_text_pdf(tmp_path: Path) -> Path:
    """A PDF with pages but zero extractable text anywhere (simulates a scanned,
    image-only document) — this must be a required-stage failure."""
    doc = pymupdf.open()
    doc.new_page()
    doc.new_page()
    pdf_path = tmp_path / "blank.pdf"
    doc.save(pdf_path)
    doc.close()
    return pdf_path


@pytest.fixture
def invalid_pdf(tmp_path: Path) -> Path:
    """A file with a .pdf extension that is not actually a valid PDF."""
    pdf_path = tmp_path / "corrupt.pdf"
    pdf_path.write_bytes(b"this is not a pdf file at all, just garbage bytes 0000")
    return pdf_path
