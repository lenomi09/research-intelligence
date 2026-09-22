# Implementation Plan

**Status:** Phase 0 — Planning
**Last updated:** 2026-09-22

This document sequences work into phases and sprints, and defines Sprint 1 in detail.
Sprints are directional, not fixed-duration — a solo developer should re-plan after each
sprint based on what was learned. See `product-backlog.md` for the itemized backlog
these sprints draw from, and `decisions.md` for the reasoning behind sequencing
deterministic pipelines before any agentic layer.

## Roadmap Overview

| Phase / Sprint | Name | Primary output |
|---|---|---|
| Phase 0 | Planning | This documentation set and repository scaffolding |
| Sprint 1 | Scientific paper ingestion | Reliable PDF → text/tables/figures/references/metadata pipeline |
| Sprint 2 | Paper discovery and retrieval | Curated-collection input + embedding-based evidence retrieval |
| Sprint 3 | Structured paper understanding | Per-paper extraction: problem, method, dataset, metric, result, limitation |
| Sprint 4 | Research landscape and clustering | Thematic clustering and method/dataset relationship surfacing |
| Sprint 5 | Multi-paper comparison | Structured, evidence-traceable comparison across papers |
| Sprint 6 | Evidence-based research gap analysis | Gap hypotheses with supporting evidence, never bare claims |
| Sprint 7 | Research graph | Paper/method/dataset/author relationship graph |
| Sprint 8 | Multimodal paper understanding | VLM-assisted figure/diagram/table understanding |
| Future | Research workflow automation and agentic capabilities | Dynamic tool selection on top of the pipelines above |

Sprints 1–3 constitute the MVP (see `PRD.md`). Sprints 4–8 build the platform's
differentiating capabilities on top of that foundation. The agentic layer is
deliberately last — see the sequencing ADR in `decisions.md`.

---

### Phase 0 — Planning

- **Objective:** Establish shared understanding of the Research Intelligence Platform's
  scope, architecture, and process before writing application code.
- **Deliverables:** `docs/` (this set), initial repository structure, `README.md`.
- **Dependencies:** None.
- **Definition of done:** All documents in `docs/` exist, are internally consistent, and
  reflect the platform's multi-paper positioning; repository structure created; Sprint 1
  defined.
- **Risks:** Over-planning / analysis paralysis. Mitigated by keeping Sprint 1 narrow and
  time-boxed.

### Sprint 1 — Scientific Paper Ingestion

- **Objective:** Reliably turn a small collection of scientific PDFs into structured,
  provenance-tagged content: text, tables, figures, references, and page metadata.
- **Deliverables:** `DocumentParser` interface + at least one implementation; ingestion
  pipeline (`src/ingestion`) that persists parsed output; a small corpus of test papers.
- **Dependencies:** Phase 0.
- **Definition of done:** Given a small set of representative AI/CV/ML papers, the
  pipeline extracts text with page provenance, extracts tables as structured data,
  extracts figures with captions, and extracts references, for the majority of the test
  corpus, with failures logged rather than silent.
- **Risks:** Multi-column layouts, inline/overlapping figures, malformed tables,
  inconsistent reference formatting. Parser choice may need revisiting after real
  testing (kept swappable per NFR-009).
- **Full detail:** see "Sprint 1 (Detailed)" below.

### Sprint 2 — Paper Discovery and Retrieval

- **Objective:** Accept a curated paper collection as input and retrieve relevant text
  evidence across it — the supporting capability everything else is built on.
- **Deliverables:** `EmbeddingProvider` + `VectorStore` interfaces and implementations;
  chunking strategy; retrieval pipeline (`src/retrieval`); collection-input handling
  (`src/discovery`, MVP scope: manual collection input, FR-020/FR-022 — not crawling).
- **Dependencies:** Sprint 1 (needs structured text + provenance).
- **Definition of done:** For a small manually curated question set, the system returns
  retrieved evidence with page citations across the full collection, judged relevant by
  manual review (see `evaluation.md`).
- **Risks:** Chunking strategy affects retrieval quality significantly; retrieval across
  a multi-paper collection needs paper-scoped filtering, not just a single flat index.

### Sprint 3 — Structured Paper Understanding

- **Objective:** Extract comparable structured fields (problem, method, dataset, metric,
  result, limitation) per paper, each with an evidence pointer — completing the MVP.
- **Deliverables:** `LLMProvider`-backed extraction pipeline (`src/understanding`);
  structured domain models for extracted fields (Method, Dataset, Metric, Experiment —
  see `architecture.md` §7); evidence-pointer plumbing reused by later Comparison/Gap
  Analysis work.
- **Dependencies:** Sprint 1 (structured text), Sprint 2 (retrieval pattern + citation
  approach established).
- **Definition of done:** MVP definition in `PRD.md` is met: for the test corpus, the
  system extracts structured fields for the majority of papers, each traceable to its
  source evidence, and answers text-based questions with citations as a byproduct.
- **Risks:** Extraction accuracy for free-text fields (method, limitation) is harder than
  simple retrieval; errors here will propagate into every later capability, so this
  sprint's accuracy sets a ceiling for Sprints 4–7.

### Sprint 4 — Research Landscape and Clustering

- **Objective:** Surface thematic structure across the collection.
- **Deliverables:** Clustering pipeline (`src/landscape`) grouping papers by theme;
  method/dataset relationship surfacing across the collection.
- **Dependencies:** Sprint 3 (needs structured fields to cluster on).
- **Definition of done:** For the test corpus, the system produces a landscape view
  (clusters + labels) that a human judges as a reasonable grouping, measured via
  clustering metrics in `evaluation.md`.
- **Risks:** Small collection size limits clustering signal; cluster labels generated by
  an LLM need the same evidence-traceability discipline as other outputs.

### Sprint 5 — Multi-Paper Comparison

- **Objective:** Compare 2+ papers across structured fields with evidence traceability —
  the platform's core differentiator.
- **Deliverables:** Comparison pipeline (`src/comparison`) producing a per-field
  comparison table/output, each cell traceable to its source paper/page.
- **Dependencies:** Sprint 3 (structured fields to compare).
- **Definition of done:** System answers a comparison question across ≥2 papers with a
  citation for each compared field, measured against comparison metrics in
  `evaluation.md`.
- **Risks:** Field alignment across papers with different terminology (e.g. different
  names for the same metric) is non-trivial and may need explicit normalization logic.

### Sprint 6 — Evidence-Based Research Gap Analysis

- **Objective:** Identify candidate underexplored topics/combinations/recurring
  limitations, always framed as hypotheses with supporting evidence.
- **Deliverables:** Gap-analysis pipeline (`src/gap_analysis`) built on Landscape +
  Understanding output; hard requirement (FR-061/NFR-012) that every output states
  supporting evidence counts and a supporting-paper list, never a bare claim.
- **Dependencies:** Sprint 4 (landscape), Sprint 3 (structured fields).
- **Definition of done:** For the test corpus, the system produces at least one gap
  hypothesis with correctly cited supporting evidence, reviewed for both evidence
  correctness and appropriate hedging language (no "this is a research gap" framing).
- **Risks:** False-positive gap claims (see `evaluation.md` "false-positive gap rate");
  small collection size limits how confidently any gap can be framed even as a
  hypothesis — this must be reflected honestly in the output, not hidden.

### Sprint 7 — Research Graph

- **Objective:** Represent paper–paper, paper–method, paper–dataset, paper–author,
  paper–topic relationships explicitly.
- **Deliverables:** Graph construction (`src/graph`) from data already extracted in
  Sprints 1–4; a query/traversal capability (relational modeling in PostgreSQL as the
  initial candidate — see `architecture.md` §6/§10; a dedicated graph database evaluated
  only if warranted).
- **Dependencies:** Sprints 1, 3, 4 (needs citations, structured fields, and topics).
- **Definition of done:** System answers at least one relationship query (e.g. "which
  papers cite paper X and also use dataset Y") correctly against the test corpus.
- **Risks:** Reference/citation extraction quality (Sprint 1) directly bounds graph
  completeness; graph modeling choice may need revisiting once real relationship density
  is observed.

### Sprint 8 — Multimodal Paper Understanding

- **Objective:** Extend Understanding/Comparison to figures, diagrams, and complex
  tables via VLM, as a supporting capability (not a standalone product surface).
- **Deliverables:** `VLMProvider` interface + implementation; figure/diagram
  understanding invoked from Understanding/Comparison (`src/multimodal`) when a
  structured field or comparison depends on visual content.
- **Dependencies:** Sprint 1 (figures/tables extracted), Sprint 3 (understanding
  pipeline to plug into).
- **Definition of done:** For a subset of the test corpus with figure-dependent claims,
  the system correctly incorporates VLM-derived evidence into at least one structured
  field or comparison, measured via multimodal metrics in `evaluation.md`.
- **Risks:** VLM quality/cost; this sprint's accuracy is expected to lag text-based
  Understanding, and that gap must be reported honestly, not smoothed over.

### Future — Research Workflow Automation and Agentic Capabilities

- **Objective:** Automate multi-step literature investigation on top of the
  deterministic pipelines built in Sprints 1–8.
- **Deliverables:** Tool abstractions (`src/tools`) wrapping the pipelines above; an
  agent orchestrator (`src/agent`, LangGraph candidate) that dynamically selects among
  them for a given multi-step request.
- **Dependencies:** Sprints 1–8 (agent has nothing reliable to orchestrate otherwise —
  see sequencing ADR in `decisions.md`).
- **Definition of done:** TBD — scoped when this phase is actually planned.
- **Risks:** Unnecessary or incorrect tool calls; added latency; debuggability of agent
  decisions (mitigated by observability, NFR-004).

---

## Sprint 1 (Detailed)

**Sprint goal:** Build a reliable scientific paper ingestion pipeline that extracts
metadata, text, tables, figures, citations/references, and page-level evidence from a
small paper collection.

**Explicitly not in Sprint 1:** full RAG, conversational chatbot, autonomous agent,
research gap analysis, research graph, production-scale paper crawling, complete
frontend, production deployment. Sprint 1 is ingestion-only, establishing reliable
structured scientific paper data for every later Research Intelligence capability.

### Scope

1. Define domain models for `Paper`, `Page`, `TextBlock`, `Table`, `Figure`, `Citation`
   in `src/domain/models` (data structures only, no behavior beyond basic validation).
2. Define the `DocumentParser` interface in `src/domain/interfaces`.
3. Implement one concrete parser in `src/infrastructure` (candidate: Docling, with
   PyMuPDF as a fallback if Docling proves difficult to integrate — decision to be made
   during the sprint, logged in `decisions.md`).
4. Implement the ingestion orchestration in `src/ingestion`: given a PDF path, run the
   parser and produce populated domain models, persisting extracted figures as image
   files under `data/figures/` and leaving table/text/reference data in memory or simple
   local files (a persistence *interface* may be stubbed, but a real database is out of
   scope for Sprint 1 — see `decisions.md` if this changes).
5. Extract each paper's reference list (and, where feasible, in-text citation markers)
   as structured data with page provenance (FR-011) — this is new relative to the
   original single-document-Q&A plan and exists specifically to support the future
   Research Graph (Sprint 7).
6. Collect a small corpus (3–5 open-access AI/CV/ML papers, e.g. from arXiv) into
   `data/papers/` for manual testing. (Respect source licensing/terms; store only what's
   needed for local development, not redistribution.)
7. Write unit tests (`tests/unit`) for domain models and any parser-independent logic.
8. Write integration tests (`tests/integration`) that run the real parser against the
   sample corpus and assert basic structural expectations (e.g. non-empty text, at least
   one table/figure/reference detected where the paper is known to have one).
9. Manually verify extraction quality against 2–3 papers by visual inspection; record
   findings (what worked, what didn't) — this feeds Sprint 2/3 planning, not this
   sprint's code.

### Out of Scope for Sprint 1

- Any LLM/VLM API calls.
- Any vector database or embedding step.
- Any structured field extraction (problem/method/dataset/metric — that's Sprint 3).
- Any API layer beyond a minimal script/CLI entry point (`scripts/`) to run ingestion
  locally — a full FastAPI app is not required yet unless it's trivial to stub.
- Persisting to PostgreSQL — file-based / in-memory persistence is acceptable for
  Sprint 1.

### Definition of Done

- `DocumentParser` interface exists and is implemented by at least one concrete parser.
- Running ingestion against each paper in the sample corpus produces, for the majority
  of the corpus: extracted text with page numbers, at least a best-effort table
  extraction, at least a best-effort figure extraction with page numbers, and an
  extracted reference list.
- Failures during parsing are logged with enough context to debug (paper, page, stage)
  rather than crashing the whole batch or failing silently.
- Unit and integration tests pass locally.
- Findings from manual verification are written up (can live in this doc's changelog or
  a short note) to inform Sprint 2/3 planning.

### Risks for Sprint 1

- Docling (or chosen parser) may be heavy to install/run locally, or may not handle a
  given paper's layout well — budget time to fall back to PyMuPDF for text/tables if
  needed, and treat this as a real architectural test of the `DocumentParser` interface's
  replaceability (a positive outcome either way).
- Table extraction is typically the hardest part of PDF parsing; it's acceptable for
  Sprint 1 to have partial/imperfect table extraction as long as it's honestly reported,
  not silently wrong.
- Reference/citation extraction formats vary widely across venues; best-effort extraction
  with honest failure reporting is acceptable for Sprint 1 — full citation-graph accuracy
  is validated later in Sprint 7.

---

## Changelog

- 2026-09-22: Initial plan created (Phase 0), scoped around single-document Q&A.
- 2026-09-22: Revised for the Research Intelligence Platform direction — added
  Discovery/Understanding/Landscape/Comparison/Gap Analysis/Graph sprints; reclassified
  Retrieval and Multimodal as supporting capabilities; moved the agentic layer to a
  future phase after all deterministic pipelines; added reference/citation extraction to
  Sprint 1 scope (FR-011) to support the future Research Graph.
