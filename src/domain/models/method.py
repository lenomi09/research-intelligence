from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.evidence import Determination, EvidencePointer


class Method(BaseModel):
    """A model/algorithm/technique referenced by a paper (architecture.md §7.3).

    Carries its own paper-scoped id (not just a name) so a later sprint (Comparison)
    can attach cross-paper alias/normalization metadata without a breaking model
    change — see ADR-016.
    """

    method_id: str
    name: str
    description: str | None = None
    evidence: list[EvidencePointer] = Field(default_factory=list)
    determination: Determination
