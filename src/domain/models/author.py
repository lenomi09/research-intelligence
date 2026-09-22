from __future__ import annotations

from pydantic import BaseModel


class Author(BaseModel):
    """A paper author.

    ``raw`` preserves the untouched source string an author name was parsed from
    (e.g. "Jane Doe, John Smith†") so a later sprint can re-derive a better split
    without re-parsing the PDF (see NFR-011, evidence traceability).
    """

    name: str
    raw: str | None = None
