from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.common import BoundingBox


class Table(BaseModel):
    """An extracted table, with page provenance (NFR-011).

    ``rows`` is a best-effort structured extraction (list of rows, each a list of
    cell strings; a cell is ``None`` when the parser could not read it, never an
    empty string standing in for "unknown" — see docs/decisions.md ADR-014 on why
    table extraction is explicitly best-effort in Sprint 1).
    """

    table_id: str
    page: int = Field(ge=1)
    caption: str | None = None
    rows: list[list[str | None]] = Field(default_factory=list)
    bbox: BoundingBox | None = None
