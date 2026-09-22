# Evaluation Strategy

**Status:** Sprints 1–3 implemented; Retrieval and Extraction harnesses exist (see
their sections below). Everything else below is still **Planned**.
**Last updated:** 2026-09-23

Evaluation is treated as a first-class concern from the start (NFR-010), not something
added after the system "works." This document defines *how* the Research Intelligence
Platform will be measured, across all of its capability areas — not just single-document
Q&A.

**A hard rule for this document and for the product itself:** every section below is
labeled **Planned** (defined here, not yet implemented), **Implemented** (a harness
exists but has not been run at scale), or **Experimental results** (real numbers from a
real run). As of this writing, everything is **Planned**. Do not add numbers to this
document that were not produced by an actual run, and do not claim a provider or method
is "best" without a documented comparison run through this methodology.

## Principles

- No metric is reported without a defined method for computing it.
- Small, manually curated evaluation sets are acceptable early (Sprints 1–3); a formal
  benchmark dataset is built later (Sprint 6+) once there's a stable system to evaluate.
- Evaluation should be re-runnable, so regressions are visible when components change
  (e.g. swapping an embedding model or an extraction prompt).
- Where "correctness" is subjective (e.g. faithfulness, gap-hypothesis relevance),
  define an explicit rubric for manual judgment before trying to automate it.
- Metrics for multi-paper capabilities (comparison, landscape, gap analysis) are just as
  important as retrieval/generation metrics — they are not an afterthought bolted onto a
  single-document Q&A evaluation.

## Discovery Metrics — **Planned**

Applies to `src/discovery` once external paper search exists (Sprint 2+).

- **Precision@K** — of the top-K papers returned for a topic query, the fraction
  actually relevant, per manual judgment.
- **Recall@K** — of the known-relevant papers for a topic query (from a curated set),
  the fraction present in the top-K results.
- **NDCG@K** — rank-aware relevance quality of the top-K results.

## Extraction (Understanding) Metrics — **Implemented**

Applies to `src/understanding` (Sprint 3).

- **Field accuracy** — fraction of eval items where the extracted field's text
  contains the expected substring, judged against a hand-authored known-correct set.
- **Evidence-page accuracy** — of the field-accuracy hits, the fraction whose
  resolved `EvidencePointer` page matches the expected page.

These require a small hand-labeled set of (paper → expected field values → expected
page) triples. A harness computing both exists at
`tests/evaluation/test_understanding_metrics.py`, run against
`tests/evaluation/understanding_eval_set.jsonl` — **a small hand-built synthetic
corpus (2 papers, 10 eval items) and a deterministic FAKE `LLMProvider` that returns
known-correct JSON, not a real LLM** (none was available in this environment — see
`decisions.md` ADR-016) **and not a real curated collection** (same constraint
Sprint 1/2 operated under). This demonstrates the harness mechanics work end to end
through real chunking/embedding/retrieval and the real prompting/parsing pipeline,
not validated extraction quality against a real LLM or real papers — no claim of
extraction quality is made here per this document's own rule above; see the Sprint 3
session's final report for the actual figures produced on the synthetic set.
Extraction accuracy (once measured against a real LLM and real papers) is treated as
a ceiling on every downstream capability (Comparison, Landscape, Gap Analysis) — see
`implementation-plan.md` Sprint 3 risks.

## Retrieval Metrics — **Implemented**

Applies to `src/retrieval` (Sprint 2+), used within Understanding, Comparison, and
grounded Q&A.

- **Recall@K** — of the evidence chunks known to be relevant to a question (from the
  curated eval set), the fraction present in the top-K retrieved chunks.
- **MRR (Mean Reciprocal Rank)** — average of 1/rank of the first relevant chunk across
  evaluation questions.

Both require a labeled set of (question → relevant chunk(s)/page(s)) pairs. A harness
computing both exists at `tests/evaluation/test_retrieval_metrics.py`, run against
`tests/evaluation/retrieval_eval_set.jsonl` — **only a small hand-built synthetic
corpus (3 papers, 6 questions), not a real curated collection** (none was available
in this environment, same constraint Sprint 1 operated under). This demonstrates the
harness works, not validated retrieval quality on real papers — no numbers from that
run are recorded here per this document's own rule above; see the Sprint 2 session's
final report for the actual figures produced.

## Generation / Grounded Analysis Metrics — **Planned**

Applies to answer/claim generation wherever it occurs (grounded Q&A, Understanding
extraction, Comparison output).

- **Faithfulness** — does the generated output only assert what's supported by the
  retrieved/extracted evidence? Initially judged manually via a rubric (e.g. pass/fail:
  "every claim is traceable to cited evidence"); may later be automated with an
  LLM-as-judge approach once a manual baseline exists to validate the judge against.
- **Citation / evidence accuracy** — does the cited page/figure/table actually contain
  the evidence used? Judged by checking the citation against the source PDF.
- **Answer correctness** — does the answer correctly address the question, per a human
  (or, later, a validated LLM-judge) comparing it to a reference answer?

## Multimodal Metrics — **Planned**

Applies to `src/multimodal` (Sprint 8), invoked from Understanding/Comparison.

- **Figure/diagram understanding accuracy** — fraction of figure-dependent eval items
  answered correctly, judged against a human-written reference.
- **Table understanding accuracy** — fraction of table-dependent eval items answered
  correctly, judged against the actual table contents.

Both are expected to lag text-based Understanding metrics initially, per `PRD.md`
success criteria — this is tracked and reported honestly, not smoothed over.

## Clustering (Research Landscape) Metrics — **Planned**

Applies to `src/landscape` (Sprint 4+).

- **Cluster purity** — for a labeled subset (papers manually assigned to known themes),
  the fraction of each cluster belonging to its majority label.
- **NMI (Normalized Mutual Information)** — agreement between produced clusters and a
  manual reference grouping.
- **ARI (Adjusted Rand Index)** — chance-corrected agreement between produced clusters
  and a manual reference grouping.

These require a small hand-labeled grouping of the sample corpus into themes.

## Comparison Metrics — **Planned**

Applies to `src/comparison` (Sprint 5+).

- **Factual accuracy** — fraction of compared fields (method/dataset/metric/result)
  that correctly reflect the source papers.
- **Evidence coverage** — fraction of compared fields that carry a citation at all.
- **Evidence correctness** — of the fields that carry a citation, the fraction whose
  citation actually supports the stated value.

## Gap Analysis Metrics — **Planned**

Applies to `src/gap_analysis` (Sprint 6+). These metrics matter more than most, because
a wrong or overconfident gap claim is the failure mode this document exists to prevent
(see `PRD.md` "Gap-hypothesis overreach risk" and NFR-012).

- **Evidence coverage** — fraction of gap hypotheses that cite supporting evidence
  (paper list + counts) rather than being asserted bare.
- **Evidence correctness** — of the cited supporting evidence, the fraction that
  actually supports the hypothesis as stated.
- **Expert relevance** — subjective rating (by the developer, or a domain-knowledgeable
  reviewer if available) of whether a surfaced hypothesis is a plausible, useful lead —
  acknowledged as a small-sample, non-blinded judgment at MVP scale, not a validated
  panel review.
- **False-positive gap rate** — fraction of surfaced hypotheses that, on inspection,
  don't hold up (e.g. the "gap" is actually well-covered by papers the system missed).
  This is the primary metric for catching overreach.

## Agent Metrics — **Planned, Deferred**

Applies to `src/agent` only once agentic tool selection exists (post-Sprint 8 — see
`implementation-plan.md`). Not a near-term evaluation priority, since the agent layer
itself is not scheduled until the deterministic pipelines above are proven.

- **Tool selection accuracy** — did the agent invoke the tool(s) actually needed?
- **Task success rate** — did the end-to-end interaction produce an acceptable output?
- **Unnecessary tool calls** — count of tool invocations not needed to complete the task.
- **Latency** — end-to-end time from request to output, tracked per task type.

## Benchmark Dataset Structure — **Planned** (Sprint 6+)

A future benchmark dataset will extend the small per-paper eval sets used in Sprints
1–5. Proposed structure (to be finalized when built, not before):

```
tests/evaluation/
  datasets/
    <paper_id>/
      paper.pdf                # or reference to data/papers/
      metadata_labels.json     # ground-truth title/authors/venue/date
      field_labels.json        # ground-truth method/dataset/metric/result/limitation
      questions.jsonl          # one JSON object per line:
        # {
        #   "id": "q-001",
        #   "question": "...",
        #   "type": "text" | "figure" | "table" | "comparison" | "gap",
        #   "papers": ["paper_id_a", "paper_id_b"],   # >1 for comparison/gap items
        #   "expected_answer": "...",
        #   "evidence": [
        #     {"paper_id": "paper_id_a", "page": 4, "figure_id": "fig-2"},
        #     {"paper_id": "paper_id_b", "page": 7}
        #   ]
        # }
  labels/
    topic_clusters.json        # manual theme grouping, for clustering metrics
  results/
    <run_id>/
      metrics.json              # computed metric values for that run
      predictions.jsonl         # per-item system output, for manual audit
```

This structure is a proposal for Sprint 6 planning; it should not be built out ahead of
need (avoid speculative infrastructure per `development-guidelines.md`).

## What We Will Not Do

- Report benchmark numbers before a benchmark exists.
- Claim a provider (LLM/VLM/embedding/vector store/paper source) is "best" without a
  documented comparison run through this evaluation methodology.
- Use automated LLM-judge metrics without first validating them against manual judgments
  on a subset, to catch judge bias/error.
- Present a gap-analysis or landscape output as validated fact instead of a hypothesis
  with reported evidence coverage/correctness — this is a product requirement
  (FR-061/NFR-012), not just an evaluation nicety.
