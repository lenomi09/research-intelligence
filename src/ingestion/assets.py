"""Asset-extraction pipeline stage (architecture.md §4.1): writes figure image bytes
to disk and fills in each Figure's ``image_path``.

Kept separate from parsing so a parser never touches the filesystem layout — see
Figure's docstring and DocumentParser's ParseResult docstring.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.domain.models.paper import Paper

logger = logging.getLogger(__name__)


def persist_figure_assets(
    paper: Paper, figure_assets: dict[str, bytes], paper_output_dir: Path
) -> list[str]:
    """Write each figure's image bytes under ``<paper_output_dir>/figures/`` and set
    ``Figure.image_path`` to the path relative to ``paper_output_dir``.

    Returns a list of warning strings for any figure whose bytes could not be
    written (optional-extraction failure — does not raise, per NFR-006).
    """
    warnings: list[str] = []
    figures_dir = paper_output_dir / "figures"

    for figure in paper.figures:
        image_bytes = figure_assets.get(figure.figure_id)
        if image_bytes is None:
            warnings.append(
                f"figure {figure.figure_id}: no image bytes were captured during "
                "parsing; image will not be persisted"
            )
            continue

        ext = figure.image_ext or "png"
        filename = f"{figure.figure_id}.{ext}"
        try:
            figures_dir.mkdir(parents=True, exist_ok=True)
            (figures_dir / filename).write_bytes(image_bytes)
            figure.image_path = f"figures/{filename}"
        except OSError as exc:
            warnings.append(
                f"figure {figure.figure_id}: failed to write image file: {exc}"
            )
            logger.warning(
                "stage=assets paper_id=%s figure_id=%s error=%s",
                paper.paper_id, figure.figure_id, exc,
            )

    return warnings
