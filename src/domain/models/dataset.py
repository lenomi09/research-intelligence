from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.evidence import Determination, EvidencePointer


class Dataset(BaseModel):
    """A dataset used for evaluation or training (architecture.md §7.3)."""

    dataset_id: str
    name: str
    evidence: list[EvidencePointer] = Field(default_factory=list)
    determination: Determination
