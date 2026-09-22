"""Persistence pipeline stage (architecture.md §4.1): writes the normalized Paper and
its IngestionReport to disk under data/papers/processed/<paper_id>/.

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

    _write_json(paper_dir / "metadata.json", {
        "paper_id": paper.paper_id,
        "source_path": paper.source_path,
        "title": paper.title,
        "authors": [a.model_dump() for a in paper.authors],
        "abstract": paper.abstract,
        "page_count": paper.page_count,
        "metadata_source": paper.metadata_source,
    })
    _write_json(paper_dir / "pages.json", [p.model_dump() for p in paper.pages])
    _write_json(paper_dir / "text" / "blocks.json", [b.model_dump() for b in paper.text_blocks])
    _write_json(paper_dir / "text" / "sections.json", [s.model_dump() for s in paper.sections])
    _write_json(paper_dir / "figures" / "figures.json", [f.model_dump() for f in paper.figures])
    _write_json(paper_dir / "tables" / "tables.json", [t.model_dump() for t in paper.tables])
    _write_json(
        paper_dir / "references" / "citations.json",
        [c.model_dump() for c in paper.citations],
    )
    _write_json(paper_dir / "manifest.json", {
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
    })

    return paper_dir


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
