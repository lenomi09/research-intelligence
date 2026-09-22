"""Shared value types used across domain models.

Kept deliberately small: a bounding box and nothing else. Anything more would be
speculative (see docs/development-guidelines.md, "avoiding unnecessary abstraction").
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BoundingBox(BaseModel):
    """A PDF-page bounding box in PDF points (pymupdf's native unit), top-left origin."""

    model_config = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float
