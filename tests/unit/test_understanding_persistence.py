"""Unit tests for src/understanding/persistence.py (round-trip + missing/corrupt-file
handling), mirrors tests/unit/test_persistence_load_paper.py's shape."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.understanding.models import EvidencedStatement, PaperUnderstanding
from src.understanding.persistence import (
    UnderstandingLoadError,
    load_understanding,
    persist_understanding,
)


def _understanding(**overrides: object) -> PaperUnderstanding:
    defaults: dict[str, object] = {
        "paper_id": "p1",
        "research_problem": EvidencedStatement(
            text="solve X", evidence=[], determination="stated"
        ),
        "extraction_status": "ok",
    }
    defaults.update(overrides)
    return PaperUnderstanding(**defaults)  # type: ignore[arg-type]


def test_persist_then_load_round_trips(tmp_path: Path) -> None:
    understanding = _understanding()

    path = persist_understanding(understanding, tmp_path)

    assert path == tmp_path / "p1" / "understanding.json"
    loaded = load_understanding(tmp_path / "p1")
    assert loaded == understanding


def test_persist_creates_paper_directory_if_missing(tmp_path: Path) -> None:
    understanding = _understanding(paper_id="p2")

    persist_understanding(understanding, tmp_path)

    assert (tmp_path / "p2" / "understanding.json").exists()


def test_load_missing_file_raises_understanding_load_error(tmp_path: Path) -> None:
    (tmp_path / "p1").mkdir()

    with pytest.raises(UnderstandingLoadError):
        load_understanding(tmp_path / "p1")


def test_load_corrupt_json_raises_understanding_load_error(tmp_path: Path) -> None:
    paper_dir = tmp_path / "p1"
    paper_dir.mkdir()
    (paper_dir / "understanding.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(UnderstandingLoadError):
        load_understanding(paper_dir)


def test_load_wrong_shape_raises_understanding_load_error(tmp_path: Path) -> None:
    paper_dir = tmp_path / "p1"
    paper_dir.mkdir()
    (paper_dir / "understanding.json").write_text('{"unexpected": "shape"}', encoding="utf-8")

    with pytest.raises(UnderstandingLoadError):
        load_understanding(paper_dir)
