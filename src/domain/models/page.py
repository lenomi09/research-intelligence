from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Page(BaseModel):
    """Page-level metadata and extraction health for one page of a paper.

    ``text_length`` and ``has_extraction_issue`` exist specifically so ingestion
    failures are visible per-page (NFR-006: don't silently produce empty results) —
    a page with ``text_length == 0`` on a paper that otherwise has extractable text is
    a strong signal of a scanned page or an extraction bug, not evidence the page was
    actually blank.
    """

    page_number: int = Field(ge=1)
    width: float | None = None
    height: float | None = None
    text_length: int = 0
    has_extraction_issue: bool = False

    @field_validator("text_length")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("text_length must not be negative")
        return v
