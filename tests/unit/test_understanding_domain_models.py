"""Unit tests for Sprint 3 domain models: EvidencePointer, Method, Dataset, Metric,
Experiment — construction, defaults, and field-level validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.models import Dataset, EvidencePointer, Experiment, Method, Metric


def _evidence(page: int = 3) -> EvidencePointer:
    return EvidencePointer(paper_id="paper_001", page=page, chunk_id="paper_001:block_0001:0")


def test_evidence_pointer_requires_positive_page() -> None:
    EvidencePointer(paper_id="paper_001", page=1, chunk_id="c1")  # valid
    with pytest.raises(ValidationError):
        EvidencePointer(paper_id="paper_001", page=0, chunk_id="c1")


def test_evidence_pointer_quote_is_optional() -> None:
    e = EvidencePointer(paper_id="paper_001", page=1, chunk_id="c1")
    assert e.quote is None


def test_method_carries_evidence_and_determination() -> None:
    method = Method(
        method_id="paper_001:method:0",
        name="Transformer",
        evidence=[_evidence()],
        determination="stated",
    )
    assert method.evidence[0].page == 3
    assert method.determination == "stated"
    assert method.description is None


def test_dataset_defaults_to_empty_evidence() -> None:
    dataset = Dataset(dataset_id="paper_001:dataset:0", name="COCO", determination="inferred")
    assert dataset.evidence == []


def test_metric_requires_determination() -> None:
    with pytest.raises(ValidationError):
        Metric(metric_id="paper_001:metric:0", name="F1")  # type: ignore[call-arg]


def test_determination_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        Method(
            method_id="paper_001:method:0",
            name="Transformer",
            determination="maybe",  # type: ignore[arg-type]
        )


def test_experiment_references_method_dataset_metric_by_id_not_embedded() -> None:
    experiment = Experiment(
        experiment_id="paper_001:experiment:0",
        method_id="paper_001:method:0",
        dataset_id="paper_001:dataset:0",
        metric_ids=["paper_001:metric:0", "paper_001:metric:1"],
        result="F1 = 0.87",
        result_evidence=[_evidence(page=5)],
        determination="stated",
    )
    assert experiment.method_id == "paper_001:method:0"
    assert experiment.metric_ids == ["paper_001:metric:0", "paper_001:metric:1"]
    assert experiment.result_evidence[0].page == 5


def test_experiment_defaults_to_no_metrics() -> None:
    experiment = Experiment(
        experiment_id="paper_001:experiment:0",
        method_id="paper_001:method:0",
        dataset_id="paper_001:dataset:0",
        result="92% accuracy",
        determination="inferred",
    )
    assert experiment.metric_ids == []
    assert experiment.result_evidence == []
