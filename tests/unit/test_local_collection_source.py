"""Unit tests for LocalCollectionPaperSource — hand-written processed-dir fixtures,
no real ingestion, no real embedding/vector-store libraries."""

from __future__ import annotations

import json
from pathlib import Path

from src.infrastructure.paper_sources.local_collection_source import (
    LocalCollectionPaperSource,
)


def _write_minimal_paper_dir(root: Path, paper_id: str) -> Path:
    paper_dir = root / paper_id
    (paper_dir / "text").mkdir(parents=True)
    (paper_dir / "metadata.json").write_text(
        json.dumps(
            {
                "paper_id": paper_id,
                "source_path": f"data/papers/raw/{paper_id}.pdf",
                "title": "A Paper",
                "authors": [],
                "abstract": None,
                "page_count": 1,
                "metadata_source": "unavailable",
            }
        ),
        encoding="utf-8",
    )
    (paper_dir / "text" / "blocks.json").write_text(
        json.dumps(
            [{"block_id": "block_0001", "page": 1, "text": "hello", "order": 0, "bbox": None}]
        ),
        encoding="utf-8",
    )
    return paper_dir


def test_list_papers_loads_well_formed_directories(tmp_path: Path) -> None:
    _write_minimal_paper_dir(tmp_path, "paper_001")
    _write_minimal_paper_dir(tmp_path, "paper_002")

    source = LocalCollectionPaperSource(processed_root=tmp_path)
    papers = source.list_papers()

    assert {p.paper_id for p in papers} == {"paper_001", "paper_002"}


def test_list_papers_skips_directory_missing_metadata(tmp_path: Path) -> None:
    _write_minimal_paper_dir(tmp_path, "paper_good")
    (tmp_path / "paper_bad").mkdir()  # no metadata.json, no text/blocks.json at all

    source = LocalCollectionPaperSource(processed_root=tmp_path)
    papers = source.list_papers()

    assert {p.paper_id for p in papers} == {"paper_good"}


def test_list_papers_on_empty_processed_root_returns_empty_list(tmp_path: Path) -> None:
    source = LocalCollectionPaperSource(processed_root=tmp_path)
    assert source.list_papers() == []


def test_list_papers_on_nonexistent_processed_root_returns_empty_list(tmp_path: Path) -> None:
    source = LocalCollectionPaperSource(processed_root=tmp_path / "does_not_exist")
    assert source.list_papers() == []


def test_list_papers_ignores_non_directory_entries(tmp_path: Path) -> None:
    _write_minimal_paper_dir(tmp_path, "paper_001")
    (tmp_path / "stray_file.txt").write_text("not a paper dir", encoding="utf-8")

    source = LocalCollectionPaperSource(processed_root=tmp_path)
    papers = source.list_papers()

    assert {p.paper_id for p in papers} == {"paper_001"}


def test_one_malformed_paper_does_not_crash_the_whole_batch(tmp_path: Path) -> None:
    """Regression test: a paper directory with syntactically valid but structurally
    wrong JSON (e.g. metadata.json missing 'paper_id') must be skipped, not crash
    list_papers() for every other paper in the collection (NFR-006)."""
    _write_minimal_paper_dir(tmp_path, "paper_good_1")
    _write_minimal_paper_dir(tmp_path, "paper_good_2")

    malformed_dir = tmp_path / "paper_malformed"
    (malformed_dir / "text").mkdir(parents=True)
    (malformed_dir / "metadata.json").write_text(
        json.dumps({"title": "No paper_id key at all"}), encoding="utf-8"
    )
    (malformed_dir / "text" / "blocks.json").write_text("[]", encoding="utf-8")

    source = LocalCollectionPaperSource(processed_root=tmp_path)
    papers = source.list_papers()

    assert {p.paper_id for p in papers} == {"paper_good_1", "paper_good_2"}
