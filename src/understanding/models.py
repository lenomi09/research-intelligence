"""Understanding's own output types — not yet documented as cross-cutting entities
in architecture.md §7.3 (unlike Method/Dataset/Metric/Experiment, which are). See
ADR-016 for why EvidencedStatement lives here rather than in src/domain/models, and
why it is named separately from architecture.md's later-sprint `ResearchClaim`
entity rather than claiming to be it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.domain.models.dataset import Dataset
from src.domain.models.evidence import Determination, EvidencePointer
from src.domain.models.experiment import Experiment
from src.domain.models.method import Method
from src.domain.models.metric import Metric

ExtractionStatus = Literal["ok", "partial", "failed"]
"""ok: at least one field extracted with grounded evidence. partial: the LLM call
succeeded and returned valid JSON, but every field ended up with no grounded
evidence (all cited labels were invalid, or none were cited) — surfaced distinctly
from "ok" rather than silently treated as success (see prompting.py). failed: the
LLM call itself failed, or its response could not be parsed as valid JSON at all."""


class EvidencedStatement(BaseModel):
    """A free-text statement extracted from a paper's own language, with evidence —
    used for both `research_problem` and each entry in `limitations`. One generic
    type rather than two near-identical classes: both are "a statement + evidence +
    stated/inferred," with no field asymmetry between them (unlike Method/Dataset/
    Metric, which participate in Experiment's join and may need cross-paper
    identity later)."""

    text: str
    evidence: list[EvidencePointer] = Field(default_factory=list)
    determination: Determination


class PaperUnderstanding(BaseModel):
    """The per-paper aggregate root Understanding produces — mirrors Paper's role
    in Sprint 1. Persisted as data/papers/processed/<paper_id>/understanding.json."""

    paper_id: str
    research_problem: EvidencedStatement | None = None
    methods: list[Method] = Field(default_factory=list)
    datasets: list[Dataset] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    experiments: list[Experiment] = Field(default_factory=list)
    limitations: list[EvidencedStatement] = Field(default_factory=list)
    extraction_status: ExtractionStatus
    warnings: list[str] = Field(default_factory=list)
