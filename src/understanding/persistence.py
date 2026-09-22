"""Persistence for Understanding's output (architecture.md §4.3 / plan §Persistence):
writes/reads a single ``understanding.json`` per paper, sibling to Sprint 1's
``metadata.json`` under ``data/papers/processed/<paper_id>/`` — there are no binary
assets here (unlike ``figures/``), so one file is enough, unlike ingestion's
multi-file layout (see ``src/ingestion/persistence.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from src.understanding.models import PaperUnderstanding

UNDERSTANDING_FILENAME = "understanding.json"


def persist_understanding(understanding: PaperUnderstanding, output_root: Path) -> Path:
    """Write ``understanding`` under ``<output_root>/<paper_id>/understanding.json``.

    Assumes ``<output_root>/<paper_id>/`` already exists (created by
    ``persist_paper`` during ingestion) but creates it if not, so Understanding
    never depends on ingestion having run in the same process.
    """
    paper_dir = output_root / understanding.paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    path = paper_dir / UNDERSTANDING_FILENAME
    path.write_text(
        json.dumps(understanding.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return path


class UnderstandingLoadError(Exception):
    """Raised when a paper's ``understanding.json`` cannot be loaded — distinct from
    ``PaperLoadError`` (ingestion) because "not yet understood" (file doesn't exist,
    e.g. Sprint 3 hasn't run for this paper) is an expected, different condition from
    ingestion's "corrupt/missing required file for a paper that must exist."
    """


def load_understanding(paper_dir: Path) -> PaperUnderstanding:
    """Reconstruct a ``PaperUnderstanding`` from a directory previously written by
    ``persist_understanding``. Raises ``UnderstandingLoadError`` — never a raw
    ``OSError``/``ValidationError`` — if the file is missing, corrupt, or doesn't
    match ``PaperUnderstanding``'s shape.
    """
    path = paper_dir / UNDERSTANDING_FILENAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnderstandingLoadError(
            f"'{paper_dir}': '{UNDERSTANDING_FILENAME}' is missing or corrupt: {exc}"
        ) from exc

    try:
        return PaperUnderstanding(**raw)
    except (TypeError, ValidationError) as exc:
        raise UnderstandingLoadError(
            f"'{paper_dir}': '{UNDERSTANDING_FILENAME}' has an unexpected shape: {exc}"
        ) from exc
