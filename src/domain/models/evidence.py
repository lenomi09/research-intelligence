from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Determination = Literal["stated", "inferred"]
"""Whether an extracted value was explicitly written in the source text ("stated")
or synthesized/paraphrased by the LLM from surrounding context ("inferred") — the
user-facing distinction between explicit facts and interpretation. See ADR-016."""


class EvidencePointer(BaseModel):
    """Points at the exact retrieved chunk a field/statement was derived from
    (ADR-009). Always resolved by code from a real EvidenceChunk (paper_id/page/
    chunk_id) — never from an LLM-invented value; see
    src/understanding/prompting.py's label-resolution step for how this is enforced.
    """

    paper_id: str
    page: int = Field(ge=1)
    chunk_id: str
    quote: str | None = None
