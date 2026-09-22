from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.common import BoundingBox


class Figure(BaseModel):
    """An extracted figure/diagram/chart image, with page provenance (NFR-011).

    ``image_path`` is ``None`` immediately after parsing and is filled in by the
    ingestion pipeline's asset-extraction stage once the image bytes are written to
    disk (see src/ingestion/assets.py) — the domain model itself never carries raw
    image bytes, so it stays cleanly JSON-serializable for persistence/validation.
    ``caption`` is only populated when a caption was actually located near the image;
    it is left ``None`` rather than fabricated when no caption is found (NFR-006).
    """

    figure_id: str
    page: int = Field(ge=1)
    caption: str | None = None
    image_path: str | None = None
    image_ext: str | None = None
    bbox: BoundingBox | None = None
