"""Unit tests for src/understanding/prompting.py — pure functions, no LLM, no real
retrieval infra (collect_labeled_evidence uses the same fake EmbeddingProvider/
VectorStore pattern as tests/unit/test_retrieval_pipeline.py)."""

from __future__ import annotations

from src.domain.interfaces.embedding_provider import EmbeddingProvider, Vector
from src.domain.interfaces.vector_store import ScoredChunk, VectorRecord, VectorStore
from src.domain.models.paper import Paper
from src.retrieval.retrieval import EvidenceChunk, RetrievalPipeline
from src.understanding.prompting import (
    LabeledEvidence,
    ParsedExtraction,
    ResolvedField,
    build_extraction_prompt,
    build_paper_understanding,
    collect_labeled_evidence,
    parse_extraction_response,
)


def _paper(**overrides: object) -> Paper:
    defaults: dict[str, object] = {
        "paper_id": "p1",
        "source_path": "paper.pdf",
        "title": "A Great Paper",
        "abstract": "We study X.",
        "page_count": 10,
        "metadata_source": "pdf_metadata",
    }
    defaults.update(overrides)
    return Paper(**defaults)  # type: ignore[arg-type]


def _chunk(
    chunk_id: str, page: int = 1, text: str = "some evidence text", score: float = 0.5
) -> EvidenceChunk:
    return EvidenceChunk(paper_id="p1", page=page, chunk_id=chunk_id, text=text, score=score)


# ---------------------------------------------------------------------------
# build_extraction_prompt
# ---------------------------------------------------------------------------


def test_build_extraction_prompt_includes_title_abstract_and_labeled_evidence() -> None:
    paper = _paper()
    evidence = [LabeledEvidence(label="E1", evidence=_chunk("c1", page=3, text="chunk text"))]

    prompt = build_extraction_prompt(paper, evidence)

    assert "A Great Paper" in prompt
    assert "We study X." in prompt
    assert "[E1] (page 3): chunk text" in prompt
    assert "Only cite evidence labels shown above" in prompt


def test_build_extraction_prompt_handles_missing_title_and_abstract() -> None:
    paper = _paper(title=None, abstract=None)

    prompt = build_extraction_prompt(paper, [])

    assert "Evidence:" in prompt


# ---------------------------------------------------------------------------
# parse_extraction_response — malformed input
# ---------------------------------------------------------------------------


def test_parse_extraction_response_unparseable_json_fails_whole_paper() -> None:
    result = parse_extraction_response("not json at all", [], "p1")

    assert result.status == "failed"
    assert result.research_problem is None
    assert result.methods == []
    assert any("could not parse" in w for w in result.warnings)


def test_parse_extraction_response_non_object_json_fails_whole_paper() -> None:
    result = parse_extraction_response("[1, 2, 3]", [], "p1")

    assert result.status == "failed"


# ---------------------------------------------------------------------------
# parse_extraction_response — field value / evidence rules
# ---------------------------------------------------------------------------


def test_parse_extraction_response_null_research_problem_is_not_an_error() -> None:
    result = parse_extraction_response('{"research_problem": null}', [], "p1")

    assert result.research_problem is None
    assert result.warnings == []


def test_parse_extraction_response_resolves_valid_evidence_label() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1", page=2))]
    raw = (
        '{"research_problem": {"value": "solve X", "evidence_labels": ["E1"], '
        '"determination": "stated"}}'
    )

    result = parse_extraction_response(raw, labeled, "p1")

    assert result.status == "ok"
    assert result.research_problem is not None
    assert result.research_problem.data["value"] == "solve X"
    assert len(result.research_problem.evidence) == 1
    pointer = result.research_problem.evidence[0]
    assert pointer.paper_id == "p1"
    assert pointer.page == 2
    assert pointer.chunk_id == "c1"


def test_parse_extraction_response_unknown_label_dropped_with_warning_field_kept() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1"))]
    raw = (
        '{"research_problem": {"value": "solve X", "evidence_labels": ["E1", "E9"], '
        '"determination": "stated"}}'
    )

    result = parse_extraction_response(raw, labeled, "p1")

    assert result.research_problem is not None
    assert result.research_problem.data["value"] == "solve X"
    assert len(result.research_problem.evidence) == 1
    assert any("unknown evidence label 'E9'" in w for w in result.warnings)


def test_parse_extraction_response_only_unknown_labels_drops_field() -> None:
    raw = (
        '{"research_problem": {"value": "solve X", "evidence_labels": ["E9"], '
        '"determination": "stated"}}'
    )

    result = parse_extraction_response(raw, [], "p1")

    # A value with zero grounded evidence is not a claim this pipeline stands
    # behind (ADR-009) — dropped entirely, not kept as an unevidenced "fact".
    assert result.research_problem is None
    assert any("no grounded evidence" in w for w in result.warnings)
    assert result.status == "partial"


def test_parse_extraction_response_uncited_field_is_dropped() -> None:
    raw = '{"research_problem": {"value": "solve X", "evidence_labels": []}}'

    result = parse_extraction_response(raw, [], "p1")

    assert result.research_problem is None
    assert result.status == "partial"


def test_parse_extraction_response_duplicate_evidence_label_not_double_counted() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1"))]
    raw = (
        '{"research_problem": {"value": "solve X", "evidence_labels": ["E1", "E1"], '
        '"determination": "stated"}}'
    )

    result = parse_extraction_response(raw, labeled, "p1")

    assert result.research_problem is not None
    assert len(result.research_problem.evidence) == 1


def test_parse_extraction_response_missing_determination_defaults_to_inferred() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1"))]
    raw = '{"research_problem": {"value": "solve X", "evidence_labels": ["E1"]}}'

    result = parse_extraction_response(raw, labeled, "p1")

    assert result.research_problem is not None
    assert result.research_problem.data["determination"] == "inferred"


def test_parse_extraction_response_empty_response_is_partial() -> None:
    result = parse_extraction_response("{}", [], "p1")

    assert result.status == "partial"
    assert result.research_problem is None
    assert result.methods == []


def test_parse_extraction_response_all_fields_ungrounded_is_partial() -> None:
    raw = (
        '{"research_problem": {"value": "solve X", "evidence_labels": []}, '
        '"methods": [{"name": "M1", "evidence_labels": []}]}'
    )

    result = parse_extraction_response(raw, [], "p1")

    assert result.status == "partial"


def test_parse_extraction_response_some_grounded_is_ok() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1"))]
    raw = (
        '{"research_problem": {"value": "solve X", "evidence_labels": ["E1"]}, '
        '"limitations": [{"value": "no code released", "evidence_labels": []}]}'
    )

    result = parse_extraction_response(raw, labeled, "p1")

    assert result.status == "ok"
    # The grounded research_problem makes the paper "ok" overall, but the
    # uncited limitation is still dropped individually — status is a paper-level
    # signal, not a per-field waiver of the evidence requirement.
    assert result.limitations == []
    assert any("limitations[0]: no grounded evidence" in w for w in result.warnings)


def test_parse_extraction_response_methods_list_parsed_with_description() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1"))]
    raw = (
        '{"methods": [{"name": "Transformer", "description": "attention-based", '
        '"evidence_labels": ["E1"], "determination": "stated"}]}'
    )

    result = parse_extraction_response(raw, labeled, "p1")

    assert len(result.methods) == 1
    assert result.methods[0].data["name"] == "Transformer"
    assert result.methods[0].data["description"] == "attention-based"


def test_parse_extraction_response_experiments_missing_required_fields_dropped() -> None:
    raw = '{"experiments": [{"method_name": "M1"}]}'

    result = parse_extraction_response(raw, [], "p1")

    assert result.experiments == []
    assert any("missing method_name/dataset_name/result" in w for w in result.warnings)


def test_parse_extraction_response_experiments_parsed_with_metric_names() -> None:
    labeled = [LabeledEvidence(label="E1", evidence=_chunk("c1"))]
    raw = (
        '{"experiments": [{"method_name": "M1", "dataset_name": "D1", '
        '"metric_names": ["Accuracy"], "result": "92%", "evidence_labels": ["E1"]}]}'
    )

    result = parse_extraction_response(raw, labeled, "p1")

    assert len(result.experiments) == 1
    assert result.experiments[0].data["method_name"] == "M1"
    assert result.experiments[0].data["metric_names"] == ["Accuracy"]


def test_parse_extraction_response_experiments_with_no_grounded_evidence_dropped() -> None:
    raw = (
        '{"experiments": [{"method_name": "M1", "dataset_name": "D1", '
        '"metric_names": [], "result": "92%", "evidence_labels": []}]}'
    )

    result = parse_extraction_response(raw, [], "p1")

    assert result.experiments == []
    assert any("experiments[0]: no grounded evidence" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# build_paper_understanding
# ---------------------------------------------------------------------------


def test_build_paper_understanding_failed_status_short_circuits() -> None:
    parsed = ParsedExtraction(
        research_problem=None,
        methods=[],
        datasets=[],
        metrics=[],
        experiments=[],
        limitations=[],
        status="failed",
        warnings=["could not parse LLM response as JSON: boom"],
    )

    pu = build_paper_understanding("p1", parsed)

    assert pu.paper_id == "p1"
    assert pu.extraction_status == "failed"
    assert pu.warnings == ["could not parse LLM response as JSON: boom"]
    assert pu.methods == []


def test_build_paper_understanding_assigns_ids_and_resolves_experiment_references() -> None:
    parsed = ParsedExtraction(
        research_problem=ResolvedField(
            data={"value": "solve X", "determination": "stated"}, evidence=[]
        ),
        methods=[
            ResolvedField(data={"name": "Transformer", "determination": "stated"}, evidence=[])
        ],
        datasets=[
            ResolvedField(data={"name": "SQuAD", "determination": "stated"}, evidence=[])
        ],
        metrics=[ResolvedField(data={"name": "F1", "determination": "stated"}, evidence=[])],
        experiments=[
            ResolvedField(
                data={
                    "method_name": "Transformer",
                    "dataset_name": "SQuAD",
                    "metric_names": ["F1"],
                    "result": "88.2",
                    "determination": "stated",
                },
                evidence=[],
            )
        ],
        limitations=[
            ResolvedField(
                data={"value": "small test set", "determination": "inferred"}, evidence=[]
            )
        ],
        status="ok",
        warnings=[],
    )

    pu = build_paper_understanding("p1", parsed)

    assert pu.extraction_status == "ok"
    assert pu.research_problem is not None
    assert pu.research_problem.text == "solve X"
    assert len(pu.methods) == 1
    method_id = pu.methods[0].method_id
    assert method_id.startswith("p1:method:")
    assert len(pu.datasets) == 1
    dataset_id = pu.datasets[0].dataset_id
    assert len(pu.metrics) == 1
    metric_id = pu.metrics[0].metric_id
    assert len(pu.experiments) == 1
    experiment = pu.experiments[0]
    assert experiment.method_id == method_id
    assert experiment.dataset_id == dataset_id
    assert experiment.metric_ids == [metric_id]
    assert experiment.result == "88.2"
    assert len(pu.limitations) == 1
    assert pu.limitations[0].text == "small test set"


def test_build_paper_understanding_drops_experiment_with_unresolvable_method_name() -> None:
    parsed = ParsedExtraction(
        research_problem=None,
        methods=[],
        datasets=[
            ResolvedField(data={"name": "SQuAD", "determination": "stated"}, evidence=[])
        ],
        metrics=[],
        experiments=[
            ResolvedField(
                data={
                    "method_name": "Unknown Method",
                    "dataset_name": "SQuAD",
                    "metric_names": [],
                    "result": "88.2",
                    "determination": "stated",
                },
                evidence=[],
            )
        ],
        limitations=[],
        status="ok",
        warnings=[],
    )

    pu = build_paper_understanding("p1", parsed)

    assert pu.experiments == []
    assert any("could not resolve method" in w for w in pu.warnings)


def test_build_paper_understanding_matches_names_case_insensitively() -> None:
    parsed = ParsedExtraction(
        research_problem=None,
        methods=[
            ResolvedField(data={"name": "Transformer", "determination": "stated"}, evidence=[])
        ],
        datasets=[
            ResolvedField(data={"name": "SQuAD", "determination": "stated"}, evidence=[])
        ],
        metrics=[],
        experiments=[
            ResolvedField(
                data={
                    "method_name": "transformer",
                    "dataset_name": "squad",
                    "metric_names": [],
                    "result": "88.2",
                    "determination": "stated",
                },
                evidence=[],
            )
        ],
        limitations=[],
        status="ok",
        warnings=[],
    )

    pu = build_paper_understanding("p1", parsed)

    assert len(pu.experiments) == 1


# ---------------------------------------------------------------------------
# collect_labeled_evidence
# ---------------------------------------------------------------------------


class _FakeEmbeddingProvider(EmbeddingProvider):
    @property
    def dimension(self) -> int:
        return 1

    def embed_documents(self, texts: list[str]) -> list[Vector]:
        return [[0.0] for _ in texts]

    def embed_query(self, text: str) -> Vector:
        return [1.0]


class _FakeVectorStore(VectorStore):
    def __init__(self, hits: list[ScoredChunk]) -> None:
        self._hits = hits

    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    def query(
        self, vector: Vector, top_k: int = 5, paper_ids: list[str] | None = None
    ) -> list[ScoredChunk]:
        return self._hits

    def delete_paper(self, paper_id: str) -> None:
        raise NotImplementedError


def test_collect_labeled_evidence_dedupes_and_labels_by_score_desc() -> None:
    hits = [
        ScoredChunk(chunk_id="c1", paper_id="p1", page=1, text="a" * 10, score=0.4),
        ScoredChunk(chunk_id="c2", paper_id="p1", page=2, text="b" * 10, score=0.9),
    ]
    retrieval = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=_FakeVectorStore(hits)
    )

    labeled = collect_labeled_evidence("p1", retrieval)

    assert [le.label for le in labeled] == ["E1", "E2"]
    assert labeled[0].evidence.chunk_id == "c2"
    assert labeled[1].evidence.chunk_id == "c1"


def test_collect_labeled_evidence_caps_pool_by_char_budget() -> None:
    hits = [
        ScoredChunk(chunk_id="c1", paper_id="p1", page=1, text="x" * 100, score=0.9),
        ScoredChunk(chunk_id="c2", paper_id="p1", page=2, text="y" * 100, score=0.5),
    ]
    retrieval = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=_FakeVectorStore(hits)
    )

    labeled = collect_labeled_evidence("p1", retrieval, max_evidence_chars=100)

    assert len(labeled) == 1
    assert labeled[0].evidence.chunk_id == "c1"


def test_collect_labeled_evidence_empty_store_returns_empty_list() -> None:
    retrieval = RetrievalPipeline(
        embedding_provider=_FakeEmbeddingProvider(), vector_store=_FakeVectorStore([])
    )

    assert collect_labeled_evidence("p1", retrieval) == []
