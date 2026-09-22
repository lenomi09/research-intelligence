from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.common import BoundingBox


class TextBlock(BaseModel):
    """A contiguous block of body text, tagged with its source page (NFR-011).

    ``order`` is the block's reading-order index within its page, as reported by the
    parser — this is best-effort for multi-column layouts (see docs/decisions.md
    ADR-014 limitations) and should not be treated as a guaranteed logical order.
    """

    block_id: str
    page: int = Field(ge=1)
    text: str
    order: int = Field(ge=0)
    bbox: BoundingBox | None = None


class Section(BaseModel):
    """A heuristically detected section heading (e.g. "Introduction", "Method").

    Section detection in Sprint 1 is font-size/keyword heuristics, not a guarantee —
    see docs/decisions.md ADR-014. A paper with no confidently detected sections
    yields an empty ``sections`` list on ``Paper``, not fabricated ones.
    """

    section_id: str
    title: str
    page: int = Field(ge=1)
    order: int = Field(ge=0)
