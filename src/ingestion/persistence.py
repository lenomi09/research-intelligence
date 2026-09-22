"""Persistence pipeline stage (architecture.md §4.1): writes the normalized Paper and
its IngestionReport to disk under data/papers/processed/<paper_id>/, and (Sprint 2)
reads it back for Discovery/Retrieval.

See docs/decisions.md ADR-014 for why this output layout differs slightly from the
directory sketch in the Sprint 1 brief, and README.md's "Ingestion Output Layout"
section for the layout as actually implemented.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.models.paper import Paper
from src.ingestion.report import IngestionReport


def persist_paper(paper: Paper, report: IngestionReport, output_root: Path) -> Path:
    """Write ``paper`` and ``report`` under ``<output_root>/<paper.paper_id>/``.

    Returns the paper's output directory. Figure image bytes must already have been
    written by ``src.ingestion.assets.persist_figure_assets`` before this is called,
    so ``Figure.image_path`` is populated in the persisted ``figures.json``.
    """
    paper_dir = output_root / paper.paper_id
    (paper_dir / "text").mkdir(parents=True, exist_ok=True)
    (paper_dir / "figures").mkdir(parents=True, exist_ok=True)
    (paper_dir / "tables").mkdir(parents=True, exist_ok=True)
    (paper_dir / "references").mkdir(parents=True, exist_ok=True)

    _write_json(
        paper_dir / "metadata.json",
        {
            "paper_id": paper.paper_id,
            "source_path": paper.source_path,
            "title": paper.title,
            "authors": [a.model_dump() for a in paper.authors],
            "abstract": paper.abstract,
            "page_count": paper.page_count,
            "metadata_source": paper.metadata_source,
        },
    )
    _write_json(paper_dir / "pages.json", [p.model_dump() for p in paper.pages])
    _write_json(
        paper_dir / "text" / "blocks.json", [b.model_dump() for b in paper.text_blocks]
    )
    _write_json(paper_dir / "text" / "sections.json", [s.model_dump() for s in paper.sections])
    _write_json(
        paper_dir / "figures" / "figures.json", [f.model_dump() for f in paper.figures]
    )
    _write_json(paper_dir / "tables" / "tables.json", [t.model_dump() for t in paper.tables])
    _write_json(
        paper_dir / "references" / "citations.json",
        [c.model_dump() for c in paper.citations],
    )
    _write_json(
        paper_dir / "manifest.json",
        {
            "report": report.model_dump(),
            "files": {
                "metadata": "metadata.json",
                "pages": "pages.json",
                "text_blocks": "text/blocks.json",
                "sections": "text/sections.json",
                "figures": "figures/figures.json",
                "tables": "tables/tables.json",
                "citations": "references/citations.json",
            },
        },
    )

    return paper_dir


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class PaperLoadError(Exception):
    """Raised when a processed paper directory is missing/has corrupt required files
    (``metadata.json`` or ``text/blocks.json``) — this paper cannot be used for
    retrieval at all, so it is not something the caller should try to recover from."""


def load_paper(paper_dir: Path) -> Paper:
    """Reconstruct a ``Paper`` from a directory previously written by ``persist_paper``.

    ``metadata.json`` and ``text/blocks.json`` are required — a paper without them
    isn't usable for retrieval, which is this sprint's entire reason to load one
    (mirrors ``DocumentParser``'s required-vs-optional split: a document that can't
    produce usable text fails outright, see ``ParsingError``). Every other file
    (``pages.json``, ``text/sections.json``, ``figures/figures.json``,
    ``tables/tables.json``, ``references/citations.json``) is optional: if missing or
    unparseable, that field degrades to an empty list and a warning is appended to
    the returned ``Paper.warnings`` instead of raising (NFR-006) — none of those
    fields affect the text this sprint actually retrieves.
    """
    metadata = _read_required_json(paper_dir / "metadata.json", paper_dir)
    text_blocks = _read_required_json(paper_dir / "text" / "blocks.json", paper_dir)

    warnings: list[str] = []
    pages = _read_optional_json(paper_dir / "pages.json", warnings, "pages")
    sections = _read_optional_json(paper_dir / "text" / "sections.json", warnings, "sections")
    figures = _read_optional_json(paper_dir / "figures" / "figures.json", warnings, "figures")
    tables = _read_optional_json(paper_dir / "tables" / "tables.json", warnings, "tables")
    citations = _read_optional_json(
        paper_dir / "references" / "citations.json", warnings, "citations"
    )

    return Paper(
        paper_id=metadata["paper_id"],
        source_path=metadata["source_path"],
        title=metadata.get("title"),
        authors=metadata.get("authors", []),
        abstract=metadata.get("abstract"),
        page_count=metadata.get("page_count", 0),
        metadata_source=metadata.get("metadata_source", "unavailable"),
        pages=pages,
        text_blocks=text_blocks,
        sections=sections,
        figures=figures,
        tables=tables,
        citations=citations,
        warnings=warnings,
    )


def _read_required_json(path: Path, paper_dir: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PaperLoadError(
            f"'{paper_dir}': required file '{path.relative_to(paper_dir)}' is "
            f"missing or corrupt: {exc}"
        ) from exc


def _read_optional_json(path: Path, warnings: list[str], field_name: str) -> list:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(
            f"{field_name}: '{path.name}' is missing or corrupt ({exc}); loaded as empty"
        )
        return []
