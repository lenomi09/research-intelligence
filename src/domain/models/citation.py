from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """One entry from a paper's reference list, with source-page provenance.

    This is the entity architecture.md §7.1 calls ``Citation``; Sprint 1's brief also
    refers to the same concept as "Reference" — they are the same domain object, named
    ``Citation`` here to stay consistent with the existing architecture docs rather than
    introducing a second name for one thing.

    Reference/citation extraction is explicitly best-effort (FR-011): ``page`` and
    ``marker`` are ``None`` when they could not be confidently determined, rather than
    guessed (NFR-006).
    """

    citation_id: str
    raw_text: str
    page: int | None = Field(default=None, ge=1)
    marker: str | None = None
