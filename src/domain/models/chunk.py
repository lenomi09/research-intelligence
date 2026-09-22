from __future__ import annotations

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A retrievable unit of paper evidence — the unit embedded and stored in the
    VectorStore (see ADR-015).

    Not the same as ``TextBlock``: a ``TextBlock`` has no ``paper_id`` (it is only
    meaningful nested inside a ``Paper``), while a ``Chunk`` must be a self-contained
    payload the vector store can return on its own. ``source_block_id`` traces a
    chunk back to the ``TextBlock`` it came from, so evidence stays traceable to its
    origin even after chunking/splitting (ADR-009).
    """

    chunk_id: str
    paper_id: str
    page: int = Field(ge=1)
    text: str
    order: int = Field(ge=0)
    source_block_id: str
