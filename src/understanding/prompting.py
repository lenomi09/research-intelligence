"""Prompt construction and response parsing for Understanding — pure functions with
no I/O (mirrors src/retrieval/chunking.py's separation of pure logic from
src/understanding/pipeline.py's orchestration class, so this is testable without
any LLM or retrieval infrastructure at all).

Evidence traceability (ADR-009) is enforced here, not left as a prompting
convention: the LLM only ever selects among evidence labels (E1, E2, ...) we
generated from real, already-retrieved chunks — it never emits a paper_id, page,
or chunk_id itself. A cited label that doesn't exist in what we retrieved is
dropped as ungrounded, never trusted (see parse_extraction_response).
"""

from __future__ import annotations

import json
import logging
from typing import NamedTuple

from src.domain.models.dataset import Dataset
from src.domain.models.evidence import Determination, EvidencePointer
from src.domain.models.experiment import Experiment
from src.domain.models.method import Method
from src.domain.models.metric import Metric
from src.domain.models.paper import Paper
from src.retrieval.retrieval import EvidenceChunk, RetrievalPipeline
from src.understanding.models import EvidencedStatement, ExtractionStatus, PaperUnderstanding

logger = logging.getLogger(__name__)

FIELD_QUERIES: dict[str, str] = {
    "research_problem": "What problem or research question does this paper address?",
    "methods": "What method, model, or algorithm does this paper propose or use?",
    "datasets": "What dataset(s) were used for evaluation or training?",
    "metrics": "What evaluation metric(s) were used to report results?",
    "experiments": "What results were reported, tied to a method/dataset/metric combination?",
    "limitations": "What limitations does the paper state about its method or results?",
}
"""FR-030–FR-035, one fixed/deterministic retrieval query per field (ADR-006)."""

DEFAULT_TOP_K_PER_FIELD = 4
DEFAULT_MAX_EVIDENCE_CHARS = 12000


class LabeledEvidence(NamedTuple):
    label: str
    evidence: EvidenceChunk


def collect_labeled_evidence(
    paper_id: str,
    retrieval: RetrievalPipeline,
    top_k_per_field: int = DEFAULT_TOP_K_PER_FIELD,
    max_evidence_chars: int = DEFAULT_MAX_EVIDENCE_CHARS,
) -> list[LabeledEvidence]:
    """Run one retrieval query per FR-030–035 field (all scoped to this paper),
    pool and de-duplicate the results by chunk_id (keeping the best score seen),
    then label them E1, E2, ... in a deterministic order (score desc, chunk_id as
    tiebreaker) — reproducible for the same retrieval result, which matters for
    testing. Caps the pool at ``max_evidence_chars``, dropping the lowest-scored
    chunks first rather than truncating chunk text mid-sentence or crashing.
    """
    pooled: dict[str, EvidenceChunk] = {}
    for query in FIELD_QUERIES.values():
        for hit in retrieval.retrieve(query, top_k=top_k_per_field, paper_ids=[paper_id]):
            existing = pooled.get(hit.chunk_id)
            if existing is None or hit.score > existing.score:
                pooled[hit.chunk_id] = hit

    ordered = sorted(pooled.values(), key=lambda c: (-c.score, c.chunk_id))

    selected: list[EvidenceChunk] = []
    total_chars = 0
    for chunk in ordered:
        if selected and total_chars + len(chunk.text) > max_evidence_chars:
            break
        selected.append(chunk)
        total_chars += len(chunk.text)

    return [
        LabeledEvidence(label=f"E{i + 1}", evidence=chunk) for i, chunk in enumerate(selected)
    ]


def build_extraction_prompt(paper: Paper, labeled_evidence: list[LabeledEvidence]) -> str:
    """Build the single prompt sent for one paper — all six fields at once, one
    LLM call per paper (the sprint's deliberate cost-control choice)."""
    lines = [
        "You are extracting structured research information from a scientific paper.",
        "Use ONLY the evidence provided below. Do not use outside knowledge.",
        "",
    ]
    if paper.title:
        lines.append(f"Paper title: {paper.title}")
    if paper.abstract:
        lines.append(f"Abstract: {paper.abstract}")
    lines.append("")
    lines.append("Evidence:")
    for label, chunk in labeled_evidence:
        lines.append(f"[{label}] (page {chunk.page}): {chunk.text}")
    lines.append("")
    lines.append(
        "Return ONLY a single JSON object (no markdown, no commentary) with this exact "
        "shape:\n"
        "{\n"
        '  "research_problem": {"value": str, "evidence_labels": [str], '
        '"determination": "stated"|"inferred"} or null,\n'
        '  "methods": [{"name": str, "description": str or null, "evidence_labels": [str], '
        '"determination": "stated"|"inferred"}],\n'
        '  "datasets": [{"name": str, "evidence_labels": [str], '
        '"determination": "stated"|"inferred"}],\n'
        '  "metrics": [{"name": str, "evidence_labels": [str], '
        '"determination": "stated"|"inferred"}],\n'
        '  "experiments": [{"method_name": str, "dataset_name": str, "metric_names": [str], '
        '"result": str, "evidence_labels": [str], "determination": "stated"|"inferred"}],\n'
        '  "limitations": [{"value": str, "evidence_labels": [str], '
        '"determination": "stated"|"inferred"}]\n'
        "}\n"
        "Rules:\n"
        "- Only cite evidence labels shown above (e.g. E1, E2). Never invent a label or a "
        "page number of your own.\n"
        "- If a field cannot be determined from the evidence, use null (for research_problem) "
        "or an empty list (for the others) — do not guess.\n"
        '- method_name/dataset_name/metric_names in "experiments" must exactly match a "name" '
        'you used in "methods"/"datasets"/"metrics" above.'
    )
    return "\n".join(lines)


class ResolvedField(NamedTuple):
    """One parsed field-group entry: its raw text/name/etc. (as a dict, shape
    varies by field — see the parsers below) plus evidence already resolved to
    real EvidencePointers. Generic across all six fields so build_paper_understanding
    can turn each into its final domain-model type."""

    data: dict[str, object]
    evidence: list[EvidencePointer]


class ParsedExtraction(NamedTuple):
    research_problem: ResolvedField | None
    methods: list[ResolvedField]
    datasets: list[ResolvedField]
    metrics: list[ResolvedField]
    experiments: list[ResolvedField]
    limitations: list[ResolvedField]
    status: ExtractionStatus
    warnings: list[str]


def parse_extraction_response(
    raw_response: str, labeled_evidence: list[LabeledEvidence], paper_id: str
) -> ParsedExtraction:
    """Parse the LLM's JSON response, resolving evidence labels back to real
    EvidencePointers. Unparseable/non-object JSON fails the whole paper
    (``status="failed"``) — nothing in a structurally untrustworthy response is
    used. A field citing a mix of known and unknown labels keeps only the known
    ones (each unknown one dropped with a warning); a field left with zero
    resolved evidence — whether because every cited label was unknown or because
    none were cited at all — is dropped entirely (ADR-009: a value with no
    evidence pointer is not a claim this pipeline will stand behind). If nothing
    across the whole response ends up with grounded evidence, ``status="partial"``
    rather than silently "ok".
    """
    evidence_by_label = {le.label: le for le in labeled_evidence}
    warnings: list[str] = []

    try:
        data = json.loads(raw_response)
        if not isinstance(data, dict):
            raise ValueError("top-level JSON is not an object")
    except (json.JSONDecodeError, ValueError) as exc:
        return ParsedExtraction(
            research_problem=None,
            methods=[],
            datasets=[],
            metrics=[],
            experiments=[],
            limitations=[],
            status="failed",
            warnings=[f"could not parse LLM response as JSON: {exc}"],
        )

    research_problem = _parse_single(
        data.get("research_problem"),
        "value",
        (),
        "research_problem",
        evidence_by_label,
        warnings,
    )
    methods = _parse_list(
        data.get("methods"), "name", ("description",), "methods", evidence_by_label, warnings
    )
    datasets = _parse_list(
        data.get("datasets"), "name", (), "datasets", evidence_by_label, warnings
    )
    metrics = _parse_list(
        data.get("metrics"), "name", (), "metrics", evidence_by_label, warnings
    )
    limitations = _parse_list(
        data.get("limitations"), "value", (), "limitations", evidence_by_label, warnings
    )
    experiments = _parse_experiments(data.get("experiments"), evidence_by_label, warnings)

    all_resolved: list[ResolvedField] = (
        ([research_problem] if research_problem else [])
        + methods
        + datasets
        + metrics
        + experiments
        + limitations
    )
    if not all_resolved or all(not rf.evidence for rf in all_resolved):
        status: ExtractionStatus = "partial"
    else:
        status = "ok"

    return ParsedExtraction(
        research_problem=research_problem,
        methods=methods,
        datasets=datasets,
        metrics=metrics,
        experiments=experiments,
        limitations=limitations,
        status=status,
        warnings=warnings,
    )


def build_paper_understanding(paper_id: str, parsed: ParsedExtraction) -> PaperUnderstanding:
    """Turn a ParsedExtraction into the final, persistable PaperUnderstanding,
    assigning paper-scoped ids and resolving each experiment's method/dataset/
    metric name references to the ids just assigned to the extracted entries."""
    if parsed.status == "failed":
        return PaperUnderstanding(
            paper_id=paper_id, extraction_status="failed", warnings=list(parsed.warnings)
        )

    warnings = list(parsed.warnings)

    research_problem = None
    if parsed.research_problem is not None:
        research_problem = EvidencedStatement(
            text=str(parsed.research_problem.data["value"]),
            evidence=parsed.research_problem.evidence,
            determination=parsed.research_problem.data["determination"],  # type: ignore[arg-type]
        )

    methods: list[Method] = []
    method_id_by_name: dict[str, str] = {}
    for i, rf in enumerate(parsed.methods):
        method_id = f"{paper_id}:method:{i}"
        name = str(rf.data["name"])
        methods.append(
            Method(
                method_id=method_id,
                name=name,
                description=rf.data.get("description"),  # type: ignore[arg-type]
                evidence=rf.evidence,
                determination=rf.data["determination"],  # type: ignore[arg-type]
            )
        )
        method_id_by_name[name.strip().lower()] = method_id

    datasets: list[Dataset] = []
    dataset_id_by_name: dict[str, str] = {}
    for i, rf in enumerate(parsed.datasets):
        dataset_id = f"{paper_id}:dataset:{i}"
        name = str(rf.data["name"])
        datasets.append(
            Dataset(
                dataset_id=dataset_id,
                name=name,
                evidence=rf.evidence,
                determination=rf.data["determination"],  # type: ignore[arg-type]
            )
        )
        dataset_id_by_name[name.strip().lower()] = dataset_id

    metrics: list[Metric] = []
    metric_id_by_name: dict[str, str] = {}
    for i, rf in enumerate(parsed.metrics):
        metric_id = f"{paper_id}:metric:{i}"
        name = str(rf.data["name"])
        metrics.append(
            Metric(
                metric_id=metric_id,
                name=name,
                evidence=rf.evidence,
                determination=rf.data["determination"],  # type: ignore[arg-type]
            )
        )
        metric_id_by_name[name.strip().lower()] = metric_id

    experiments: list[Experiment] = []
    for i, rf in enumerate(parsed.experiments):
        method_name = str(rf.data["method_name"]).strip().lower()
        dataset_name = str(rf.data["dataset_name"]).strip().lower()
        method_id = method_id_by_name.get(method_name)
        dataset_id = dataset_id_by_name.get(dataset_name)
        if method_id is None or dataset_id is None:
            warnings.append(
                f"experiments[{i}]: could not resolve method "
                f"'{rf.data['method_name']}' or dataset '{rf.data['dataset_name']}' "
                "to an extracted entry, dropped"
            )
            continue
        metric_names = rf.data.get("metric_names") or []
        metric_ids = [
            metric_id_by_name[str(m).strip().lower()]
            for m in metric_names  # type: ignore[union-attr]
            if str(m).strip().lower() in metric_id_by_name
        ]
        experiments.append(
            Experiment(
                experiment_id=f"{paper_id}:experiment:{i}",
                method_id=method_id,
                dataset_id=dataset_id,
                metric_ids=metric_ids,
                result=str(rf.data["result"]),
                result_evidence=rf.evidence,
                determination=rf.data["determination"],  # type: ignore[arg-type]
            )
        )

    limitations = [
        EvidencedStatement(
            text=str(rf.data["value"]),
            evidence=rf.evidence,
            determination=rf.data["determination"],  # type: ignore[arg-type]
        )
        for rf in parsed.limitations
    ]

    return PaperUnderstanding(
        paper_id=paper_id,
        research_problem=research_problem,
        methods=methods,
        datasets=datasets,
        metrics=metrics,
        experiments=experiments,
        limitations=limitations,
        extraction_status=parsed.status,
        warnings=warnings,
    )


def _parse_determination(raw: object) -> Determination:
    if raw in ("stated", "inferred"):
        return raw  # type: ignore[return-value]
    return "inferred"


def _resolve_evidence(
    labels: list[object],
    evidence_by_label: dict[str, LabeledEvidence],
    warnings: list[str],
    context: str,
) -> list[EvidencePointer]:
    pointers: list[EvidencePointer] = []
    seen_labels: set[str] = set()
    for raw_label in labels:
        label = str(raw_label)
        if label in seen_labels:
            continue
        seen_labels.add(label)
        labeled = evidence_by_label.get(label)
        if labeled is None:
            warnings.append(f"{context}: cited unknown evidence label '{label}', dropped")
            continue
        chunk = labeled.evidence
        pointers.append(
            EvidencePointer(
                paper_id=chunk.paper_id,
                page=chunk.page,
                chunk_id=chunk.chunk_id,
                quote=chunk.text[:200],
            )
        )
    return pointers


def _parse_single(
    raw: object,
    text_key: str,
    extra_keys: tuple[str, ...],
    context: str,
    evidence_by_label: dict[str, LabeledEvidence],
    warnings: list[str],
) -> ResolvedField | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get(text_key)
    if not value:
        return None
    data: dict[str, object] = {
        text_key: str(value),
        "determination": _parse_determination(raw.get("determination")),
    }
    for key in extra_keys:
        if key in raw:
            data[key] = raw[key]
    labels = raw.get("evidence_labels")
    evidence = _resolve_evidence(
        labels if isinstance(labels, list) else [], evidence_by_label, warnings, context
    )
    if not evidence:
        # ADR-009 (evidence traceability is a hard requirement): a value with no
        # grounded evidence pointer is not a claim we can stand behind, so it is
        # dropped rather than persisted as an unevidenced "fact" — matches the
        # design intent recorded in ADR-016 ("keep the field only if some valid
        # label remains"), which the pre-fix version of this function violated.
        warnings.append(f"{context}: no grounded evidence, dropped")
        return None
    return ResolvedField(data=data, evidence=evidence)


def _parse_list(
    raw_list: object,
    text_key: str,
    extra_keys: tuple[str, ...],
    context: str,
    evidence_by_label: dict[str, LabeledEvidence],
    warnings: list[str],
) -> list[ResolvedField]:
    if not isinstance(raw_list, list):
        return []
    results: list[ResolvedField] = []
    for i, item in enumerate(raw_list):
        rf = _parse_single(
            item, text_key, extra_keys, f"{context}[{i}]", evidence_by_label, warnings
        )
        if rf is not None:
            results.append(rf)
    return results


def _parse_experiments(
    raw_list: object, evidence_by_label: dict[str, LabeledEvidence], warnings: list[str]
) -> list[ResolvedField]:
    if not isinstance(raw_list, list):
        return []
    results: list[ResolvedField] = []
    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            continue
        method_name = item.get("method_name")
        dataset_name = item.get("dataset_name")
        result = item.get("result")
        if not (method_name and dataset_name and result):
            warnings.append(
                f"experiments[{i}]: missing method_name/dataset_name/result, dropped"
            )
            continue
        metric_names_raw = item.get("metric_names")
        metric_names = metric_names_raw if isinstance(metric_names_raw, list) else []
        data: dict[str, object] = {
            "method_name": str(method_name),
            "dataset_name": str(dataset_name),
            "metric_names": [str(m) for m in metric_names],
            "result": str(result),
            "determination": _parse_determination(item.get("determination")),
        }
        labels = item.get("evidence_labels")
        evidence = _resolve_evidence(
            labels if isinstance(labels, list) else [],
            evidence_by_label,
            warnings,
            f"experiments[{i}]",
        )
        if not evidence:
            # Same ADR-009 rule as _parse_single — see its comment for why.
            warnings.append(f"experiments[{i}]: no grounded evidence, dropped")
            continue
        results.append(ResolvedField(data=data, evidence=evidence))
    return results
