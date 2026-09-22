from __future__ import annotations

from pydantic import BaseModel, Field

from src.domain.models.evidence import Determination, EvidencePointer


class Experiment(BaseModel):
    """A specific method+dataset+metric+result combination within a paper — the
    join point between a Paper and the Method/Dataset/Metric it used
    (architecture.md §7.3).

    References Method/Dataset/Metric by id rather than embedding them, mirroring
    Chunk.source_block_id's reference-not-nest pattern — avoids duplicate copies
    when one method is reused across multiple experiments in the same paper.
    """

    experiment_id: str
    method_id: str
    dataset_id: str
    metric_ids: list[str] = Field(default_factory=list)
    result: str
    result_evidence: list[EvidencePointer] = Field(default_factory=list)
    determination: Determination
