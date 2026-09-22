# Requirements

**Status:** Phase 0 — Planning
**Last updated:** 2026-09-22

This document defines functional and non-functional requirements for the Research
Intelligence Platform. See `PRD.md` for product context and `implementation-plan.md` for
when each requirement is targeted to be built. Requirements are grouped by capability
area, following the platform's priority order (Discovery → Ingestion → Understanding →
Retrieval/Evidence → Comparison → Landscape → Gap Analysis → Graph → Multimodal), not by
build order — see `implementation-plan.md` for the actual sprint sequence.

IDs are stable once assigned. Superseded requirements are marked `[SUPERSEDED]` rather
than renumbered or deleted. `FR-001`–`FR-010` below were originally scoped around
single-document Q&A; they are retained (renumbering avoided) but reclassified as
supporting capabilities beneath the platform's multi-paper value proposition.

## Functional Requirements — Discovery

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-020 | Paper collection input | The system shall accept a manually curated set of paper references/files as its initial collection (no crawling required for MVP). | Sprint 1 |
| FR-021 | Topic search (future) | The system shall support searching external paper sources (e.g. arXiv) by topic. | Sprint 2+ |
| FR-022 | Metadata collection | The system shall collect and store paper-level metadata (title, authors, venue, date, abstract) during ingestion. | Sprint 1 |
| FR-023 | Deduplication (future) | The system shall detect and merge duplicate paper entries (e.g. preprint vs. camera-ready). | Future, unscheduled |
| FR-024 | Filtering (future) | The system shall support filtering the paper collection by date/topic/venue. | Future, unscheduled |
| FR-025 | Relevance ranking (future) | The system shall rank discovered papers by relevance to a topic query. | Sprint 2+ |

## Functional Requirements — Ingestion

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-001 | PDF upload | The system shall accept scientific PDFs as input for a collection (via API/CLI). | Sprint 1 |
| FR-002 | Document parsing | The system shall parse an uploaded PDF into structured content (text blocks, tables, figures, page metadata). | Sprint 1 |
| FR-003 | Text extraction | The system shall extract body text with page-level provenance (which page each text block came from). | Sprint 1 |
| FR-004 | Table extraction | The system shall extract tables as structured data (rows/columns) with page and table-index provenance. | Sprint 1 |
| FR-005 | Figure extraction | The system shall extract figures/images with page and figure-index provenance, including captions when available. | Sprint 1 |
| FR-011 | Reference/citation extraction | The system shall extract the paper's reference list, and where feasible the in-text citation markers, with provenance. | Sprint 1 |

## Functional Requirements — Understanding (Structured Extraction)

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-030 | Research problem extraction | The system shall extract a paper's stated research problem/objective, with an evidence pointer. | Sprint 3 |
| FR-031 | Methodology extraction | The system shall extract the paper's method/model/algorithm, with an evidence pointer. | Sprint 3 |
| FR-032 | Dataset extraction | The system shall extract dataset(s) used, with an evidence pointer. | Sprint 3 |
| FR-033 | Metric extraction | The system shall extract evaluation metric(s) used, with an evidence pointer. | Sprint 3 |
| FR-034 | Result extraction | The system shall extract reported result(s) tied to a method/dataset/metric combination, with an evidence pointer. | Sprint 3 |
| FR-035 | Limitation extraction | The system shall extract stated limitations, with an evidence pointer. | Sprint 3 |

## Functional Requirements — Retrieval / Evidence (Supporting Capability)

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-006 | Text retrieval | The system shall retrieve relevant text chunks across one or more papers for a natural-language question, using embedding-based similarity search. | Sprint 2 |
| FR-009 | Evidence-grounded answering | The system shall generate answers/claims using only retrieved evidence, not unsourced model knowledge. | Sprint 2+ |
| FR-010 | Citations | The system shall attach citations to answers/claims/comparisons, referencing the source paper, page number, and figure/table ID where applicable. | Sprint 2+ |

## Functional Requirements — Comparison

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-050 | Multi-paper comparison | The system shall compare 2+ papers by research problem, methodology, dataset, metric, experimental setting, result, and limitation. | Sprint 5 |
| FR-051 | Comparison evidence traceability | Every field compared across papers shall retain a pointer back to the specific evidence it was extracted from. | Sprint 5 |

## Functional Requirements — Research Landscape

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-040 | Topic clustering | The system shall cluster papers in the collection by research direction/theme. | Sprint 4 |
| FR-041 | Theme identification | The system shall surface major and emerging themes across the clustered collection. | Sprint 4 |
| FR-042 | Method/dataset relationship surfacing | The system shall surface relationships between methods and datasets observed across the collection (e.g. which methods are commonly evaluated on which datasets). | Sprint 4 |

## Functional Requirements — Gap Analysis

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-060 | Gap hypothesis generation | The system shall identify candidate underexplored topics, method/dataset combinations, or recurring limitations, from patterns in the extracted/clustered data. | Sprint 6 |
| FR-061 | Hypothesis framing (hard requirement) | Every gap-analysis output shall be presented as a hypothesis supported by cited evidence (e.g. "N of M analyzed papers ..." with the supporting paper list), never as an unqualified factual claim. | Sprint 6 |

## Functional Requirements — Research Graph (Future)

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-070 | Paper-to-paper relationships | The system shall represent citation/relatedness relationships between papers. | Sprint 7 |
| FR-071 | Paper-to-method / paper-to-dataset relationships | The system shall represent which papers use which methods/datasets as graph edges. | Sprint 7 |
| FR-072 | Paper-to-author / paper-to-topic relationships | The system shall represent authorship and topic membership as graph edges. | Sprint 7 |

## Functional Requirements — Multimodal (Supporting Capability)

| ID | Requirement | Description | Target sprint |
|----|-------------|--------------|----------------|
| FR-007 | Figure analysis | The system shall use a VLM to answer or describe the content of a figure/diagram/chart when relevant to a question or comparison. | Sprint 8 |
| FR-008 | Table analysis | The system shall support querying extracted tables to answer questions about their contents, combining structured lookup and/or LLM reasoning. | Sprint 8 (basic structured table lookup may land earlier as part of Understanding) |

## Functional Requirements — Future (Beyond Sprint 8)

| ID | Requirement | Description | Notes |
|----|-------------|--------------|-------|
| FR-103 | Agentic tool selection | Dynamically select among retrieval, extraction, comparison, and other tools based on the request, replacing fixed deterministic pipelines where warranted. | Not an initial architecture driver — see ADR in `decisions.md`. |
| FR-104 | Web search tool | Augment analysis with external web search when local evidence is insufficient. | Future, unscheduled |
| FR-105 | Report generation | Generate a structured research summary/report from a paper collection. | Future, unscheduled |
| FR-106 | Model/provider switching at runtime | Switch LLM/VLM/embedding provider via configuration without redeploying code changes. | Future, unscheduled |
| FR-107 | Local model support | Support fully local LLM/VLM/embedding inference as an alternative to hosted APIs. | Future, unscheduled |
| FR-108 | Production API/UI | Harden the API and ship a usable frontend for non-developer use. | Future, unscheduled |
| FR-109 | Scanned/OCR PDF support | Support scanned (non-digital-native) PDFs via OCR. | Future, unscheduled |
| FR-110 | Advanced evaluation harness | Automated, repeatable evaluation against a benchmark dataset with tracked metrics over time. | Sprint 6+ |
| FR-111 | Automated multi-step literature investigation | Agent-driven, multi-step research workflows built on top of the deterministic pipelines. | Future, unscheduled |

## Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-001 | Maintainability | Code shall be organized by domain concern (ingestion, discovery, understanding, retrieval, landscape, comparison, gap_analysis, graph, multimodal, api) with clear module boundaries, so a change in one area does not require touching unrelated areas. |
| NFR-002 | Modularity | Each major capability (parsing, embedding, vector storage, LLM inference, VLM inference, paper source) shall be accessed through a domain-defined interface, with concrete providers implemented in `infrastructure/`. |
| NFR-003 | Testability | Domain and application logic shall be testable without live network calls, by depending on interfaces that can be faked/mocked in unit tests. |
| NFR-004 | Observability | The system shall log key pipeline steps (ingestion, extraction, retrieval, comparison, gap analysis) with enough structure to debug a wrong or unsupported output after the fact. |
| NFR-005 | Latency (informational) | Ingestion of a typical paper (<30 pages) should complete within a few minutes on developer hardware; a single query/comparison should complete within tens of seconds. These are working targets, not SLAs, and will be revisited once real measurements exist. |
| NFR-006 | Reliability | Parsing, extraction, or provider failures shall be surfaced as explicit errors/logs, not silently produce empty or fabricated results. |
| NFR-007 | Security | No credentials or API keys shall be hard-coded or committed to version control; all secrets are supplied via environment variables/config, excluded via `.gitignore`. |
| NFR-008 | Configuration management | Provider selection (LLM/VLM/embedding/vector store/parser/paper source) and other environment-dependent settings shall be controlled via configuration (env vars / config files), not hard-coded in application logic. |
| NFR-009 | Provider replaceability | It shall be possible to replace any single infrastructure provider (LLM, VLM, embedding model, vector database, document parser, paper source) by adding/changing an infrastructure implementation, without modifying domain or application logic. |
| NFR-010 | Evaluation-driven development | Each major capability (discovery, extraction, retrieval, comparison, clustering, gap analysis) shall have an associated, even if initially manual/small-scale, evaluation method defined before or alongside implementation (see `evaluation.md`). |
| NFR-011 | Evidence traceability | Every extracted field, comparison, or gap hypothesis surfaced to a user shall carry a pointer to the specific paper/page/figure/table it was derived from; outputs without a traceable source shall not be presented as evidence-backed. |
| NFR-012 | Hypothesis framing | Any output derived from statistical/clustering patterns across the collection (landscape themes, gap hypotheses) shall be explicitly labeled as a hypothesis with supporting evidence counts, not as a confirmed fact. |

## Requirement Traceability Notes

- FR-001–FR-011 (Ingestion, plus FR-020/FR-022 Discovery-input) map to Sprint 1.
- FR-006, FR-009, FR-010 (Retrieval/Evidence) underpin every later capability and are
  built in Sprint 2, but are not themselves the product's primary value proposition —
  see `PRD.md` Non-goals.
- FR-030–FR-035 (Understanding) map to Sprint 3 and are the foundation for Comparison,
  Landscape, and Gap Analysis.
- NFR-002, NFR-009, and NFR-011/NFR-012 are the basis for the interface-driven,
  evidence-traceable architecture described in `architecture.md` and for the ADRs in
  `decisions.md`.
- Requirements are not final; new FRs/NFRs should be appended (not renumbered) as scope
  evolves, and superseded requirements should be marked `[SUPERSEDED]` rather than
  deleted.
