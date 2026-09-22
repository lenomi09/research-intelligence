from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.evidence import Determination, EvidencePointer


class Metric(BaseModel):
    """An evaluation metric used to report results (architecture.md §7.3)."""

    metric_id: str
    name: str
    evidence: list[EvidencePointer] = Field(default_factory=list)
    determination: Determination
