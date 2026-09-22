# Product Backlog

**Status:** Phase 0 — Planning
**Last updated:** 2026-09-22

Priorities: **P0** = required for MVP, **P1** = important, **P2** = useful later,
**P3** = optional/future. Items are grouped by area, ordered by platform priority:
Discovery → Ingestion → Understanding → Retrieval → Landscape → Comparison → Gap
Analysis → Graph → Multimodal → Evaluation → API → Frontend → Infrastructure → DevOps.
Agent/Tools is intentionally listed last and kept minimal — it is a future orchestration
layer, not a primary product category (see `decisions.md`). IDs are stable once
assigned; superseded items are marked `[SUPERSEDED]` rather than renumbered or deleted.

This backlog is kept intentionally small — depth is added per item as it's picked up,
not by enumerating every conceivable future task now.

## Discovery

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| DISC-001 | Manual collection input | P0 | Accept a manually curated set of paper files/references as the collection (FR-020). | A list of local PDF paths/URLs can be provided and is treated as one collection. | None |
| DISC-002 | Paper metadata collection | P0 | Collect title/authors/venue/date/abstract during ingestion (FR-022). | Metadata populated for the majority of the sample corpus. | ING-006 |
| DISC-003 | `PaperSource` interface + topic search | P1 | Define `PaperSource` interface; implement search against an external source (e.g. arXiv) by topic (FR-021/FR-025). | Given a topic string, returns a ranked list of candidate papers with metadata. | DISC-002 |
| DISC-004 | Deduplication | P2 | Detect/merge duplicate paper entries (FR-023). | Two entries for the same paper (e.g. preprint + camera-ready) are merged or flagged. | DISC-003 |
| DISC-005 | Collection filtering | P2 | Filter the collection by date/topic/venue (FR-024). | Filter parameters narrow the active collection correctly. | DISC-002 |

## Ingestion

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| ING-001 | Define core domain models | P0 | `Paper`/`Page`/`TextBlock`/`Table`/`Figure`/`Citation` in `src/domain/models`. | Models exist, covered by unit tests, no dependency on any parsing library. | None |
| ING-002 | Define `DocumentParser` interface | P0 | Abstract interface any concrete parser implements. | Interface defined in `src/domain/interfaces` with documented method contracts. | ING-001 |
| ING-003 | Text extraction with page provenance | P0 | Extract body text such that every block records its source page (FR-003). | Correct page numbers for the majority of the sample corpus, spot-checked. | ING-002 |
| ING-004 | Table extraction | P0 | Extract tables as structured row/column data with provenance (FR-004). | Best-effort extraction for the majority of papers with a table; failures logged. | ING-002 |
| ING-005 | Figure extraction | P0 | Extract figure images and captions with provenance (FR-005). | Figures extracted as image files with correct page association for the majority. | ING-002 |
| ING-006 | Ingestion orchestration pipeline | P0 | Given a PDF path, run the parser and produce/persist populated domain models. | Single entry point runs end-to-end ingestion for one PDF. | ING-001–ING-005 |
| ING-007 | Reference/citation extraction | P0 | Extract each paper's reference list, with page provenance (FR-011). | References extracted for the majority of the sample corpus. | ING-002 |
| ING-008 | Sample paper corpus | P0 | Collect 3–5 open-access AI/CV/ML papers for development/testing. | Papers stored under `data/papers/` (gitignored), sources recorded. | None |
| ING-009 | Parsing failure logging | P0 | Structured logging for parse failures (paper, page, stage, error). | A forced parse failure is logged with actionable context, not silent. | ING-006 |
| ING-010 | Second `DocumentParser` implementation | P2 | Validate swappability (e.g. PyMuPDF if Docling was primary). | Both implementations pass the same integration test suite. | ING-002–ING-005 |
| ING-011 | OCR support for scanned PDFs | P3 | Parsing fallback for non-digital-native PDFs. | TBD — deferred, not scoped until prioritized. | ING-002 |

## Understanding

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| UND-001 | Define structured-field domain models | P0 | `Method`/`Dataset`/`Metric`/`Experiment` in `src/domain/models` (FR-030–FR-034). | Models exist with an evidence-pointer field; unit tested. | ING-001 |
| UND-002 | Research problem + methodology extraction | P0 | Extract stated problem and method with an evidence pointer. | Extracted for the majority of the sample corpus, judged against manual annotation. | UND-001, RET-005 |
| UND-003 | Dataset + metric extraction | P0 | Extract dataset(s) and metric(s) used, with evidence pointers. | Extracted for the majority of the sample corpus. | UND-001, RET-005 |
| UND-004 | Result extraction | P0 | Extract results tied to a method/dataset/metric combination. | Extracted for a meaningful subset of the sample corpus. | UND-003 |
| UND-005 | Limitation extraction | P1 | Extract stated limitations with evidence pointers. | Extracted where a paper states limitations explicitly. | UND-002 |
| UND-006 | Understanding evaluation | P1 | Manual/automated check of extraction accuracy per field (EXTRACT metrics). | Metrics computed against a small labeled set (see `evaluation.md`). | UND-002–UND-005, EVAL-001 |

## Retrieval (Supporting Capability)

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| RET-001 | Define `EmbeddingProvider` interface | P0 | Interface in `src/domain/interfaces`, no vendor types leaked. | Interface defined and documented. | None |
| RET-002 | Define `VectorStore` interface | P0 | Interface supporting upsert + top-K similarity query with paper-scoped filtering. | Interface defined and documented. | None |
| RET-003 | Text chunking strategy | P0 | Documented chunking approach, preserving page provenance per chunk. | Chunking applied consistently across the sample corpus. | ING-003 |
| RET-004 | Embedding + indexing pipeline | P0 | Embed and upsert text chunks into the configured vector store. | Chunks from a paper are embedded and indexed. | RET-001–RET-003 |
| RET-005 | Retrieval pipeline | P0 | Given a question/extraction target, return top-K relevant chunks with provenance, across one or more papers. | Retrieval works both single-paper- and collection-scoped. | RET-004 |
| RET-006 | Reranking | P2 | Optional reranking step to improve ordering of retrieved chunks. | Measurable improvement via RET-008. | RET-005 |
| RET-007 | Grounded answer generation with citations | P0 | Generate answers/claims using only retrieved evidence, with citations (FR-009/FR-010). | Answers cite page (and figure/table where applicable); spot-checked for hallucination. | RET-005 |
| RET-008 | Retrieval evaluation (Recall@K, MRR) | P1 | Harness computing retrieval metrics against a labeled question set. | Metrics computed and reported per `evaluation.md`. | RET-005, EVAL-001 |

## Research Landscape

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| LAND-001 | Topic clustering | P1 | Cluster papers by research direction/theme (FR-040). | Clusters produced for the sample corpus, judged reasonable by manual review. | UND-001–UND-004 |
| LAND-002 | Theme/emerging-topic labeling | P1 | Surface major/emerging themes across clusters (FR-041). | Each cluster has a human-reviewable label with supporting evidence. | LAND-001 |
| LAND-003 | Method–dataset relationship surfacing | P1 | Surface which methods are commonly evaluated on which datasets (FR-042). | Relationship summary produced and spot-checked against the corpus. | UND-003 |
| LAND-004 | Landscape evaluation | P2 | Cluster purity, NMI, ARI against a labeled grouping. | Metrics computed per `evaluation.md`. | LAND-001, EVAL-001 |

## Comparison

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| COMP-001 | Multi-paper comparison pipeline | P1 | Compare 2+ papers across problem/method/dataset/metric/setting/result/limitation (FR-050). | Given ≥2 papers, produces a per-field comparison output. | UND-001–UND-005 |
| COMP-002 | Comparison evidence traceability | P1 | Every compared field retains a pointer to its source evidence (FR-051/NFR-011). | Each comparison cell has a citation, spot-checked against the source PDFs. | COMP-001 |
| COMP-003 | Comparison evaluation | P2 | Factual accuracy, evidence coverage, evidence correctness. | Metrics computed per `evaluation.md`. | COMP-001, EVAL-001 |

## Gap Analysis

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| GAP-001 | Gap hypothesis generation | P2 | Identify candidate underexplored topics/combinations/recurring limitations (FR-060). | Produces at least one hypothesis for the sample corpus with supporting evidence. | LAND-001, UND-001–UND-005 |
| GAP-002 | Hypothesis framing enforcement | P2 | Every gap output states evidence counts + supporting-paper list; never a bare claim (FR-061/NFR-012). | Output text reviewed to confirm hedged, evidence-cited framing (see `PRD.md` example). | GAP-001 |
| GAP-003 | Gap-analysis evaluation | P3 | Evidence coverage/correctness, expert relevance, false-positive gap rate. | Metrics computed per `evaluation.md`, acknowledging small-corpus limits. | GAP-001, EVAL-001 |

## Research Graph

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| GRAPH-001 | Paper–paper relationships | P3 | Represent citation/relatedness edges (FR-070). | Graph query returns correct citing/cited papers for the sample corpus. | ING-007 |
| GRAPH-002 | Paper–method / paper–dataset relationships | P3 | Represent usage edges (FR-071). | Graph query returns correct method/dataset usage for the sample corpus. | UND-003 |
| GRAPH-003 | Paper–author / paper–topic relationships | P3 | Represent authorship/topic edges (FR-072). | Graph query returns correct author/topic membership. | DISC-002, LAND-001 |

## Multimodal (Supporting Capability)

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| MM-001 | Define `VLMProvider` interface | P1 | Interface accepting image + prompt, returning text; no vendor types leaked. | Interface defined and documented. | None |
| MM-002 | Figure/diagram understanding | P1 | Given a figure and a question/field, return a grounded description/answer via VLM (FR-007). | Correct for a meaningful subset of figure-dependent eval questions. | MM-001, ING-005 |
| MM-003 | Complex table interpretation via VLM | P2 | VLM-assisted interpretation for tables where structured extraction is insufficient (FR-008). | Improves table QA accuracy over structured-only lookup on a subset. | MM-001, ING-004 |
| MM-004 | Multimodal evaluation | P2 | Figure/table understanding accuracy against a labeled set. | Metrics computed per `evaluation.md`, explicitly reported as lagging text metrics. | MM-002, MM-003, EVAL-001 |

## Evaluation

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| EVAL-001 | Small manually curated eval set | P0 | Per sample paper: text questions + expected extraction fields + (later) comparison/gap expectations. | Stored under `tests/evaluation`, covering ingestion + understanding at minimum. | ING-008 |
| EVAL-002 | Faithfulness / evidence-accuracy review process | P0 | Documented rubric for judging faithfulness/citation accuracy by hand. | Rubric documented in `evaluation.md`; applied to a sample of outputs. | EVAL-001 |
| EVAL-003 | Automated evaluation harness | P1 | Script computing defined metrics against the eval set without manual intervention. | Runs end-to-end and reports metrics for at least Ingestion/Retrieval/Understanding. | EVAL-001, RET-007 |
| EVAL-004 | Formal benchmark dataset | P2 | Structured dataset format defined and populated beyond the initial small eval set. | Dataset follows the structure documented in `evaluation.md`. | EVAL-001 |

## API

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| API-001 | Ingestion trigger (CLI or endpoint) | P0 | Run ingestion for a given PDF path/collection. | A script or endpoint runs ingestion end-to-end. | ING-006 |
| API-002 | Question-answering / retrieval endpoint | P1 | Accept a question (single- or multi-paper) and return an answer with citations. | Endpoint returns grounded answers with citations. | RET-007 |
| API-003 | Understanding endpoint | P1 | Return structured fields for a given paper. | Endpoint returns extracted fields with evidence pointers. | UND-002–UND-004 |
| API-004 | Comparison endpoint | P2 | Return a comparison across a set of papers. | Endpoint returns a per-field comparison with citations. | COMP-001 |
| API-005 | Request/response schemas | P0 | Pydantic schemas in `src/api` or `src/domain/schemas`, decoupled from domain models. | Schemas defined for whichever endpoints exist at the time. | API-001 |
| API-006 | Error handling / translation layer | P1 | Parser/provider/extraction errors surfaced as meaningful HTTP error responses. | Forced failure returns a clear error response, not a 500 with no context. | API-001 |

## Frontend

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| FE-001 | Minimal collection + Q&A UI | P2 | React+Tailwind (candidate) page to view an ingested collection and ask questions. | Basic UI usable locally against the API. | API-002 |
| FE-002 | Comparison/landscape view | P3 | UI to view multi-paper comparisons and the landscape clustering. | Displays comparison table and cluster groupings. | FE-001, API-004 |
| FE-003 | Citation display | P2 | UI renders citations so a user can locate the source page/figure/table. | Citation link/reference is visible and correct in the UI. | FE-001 |

## Infrastructure

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| INF-001 | `DocumentParser` implementation | P0 | Docling or PyMuPDF. | Satisfies `DocumentParser` contract; passes interface test suite. | ING-002 |
| INF-002 | `EmbeddingProvider` implementation | P0 | BGE or Jina. | Satisfies `EmbeddingProvider` contract. | RET-001 |
| INF-003 | `VectorStore` implementation | P0 | Qdrant (candidate). | Satisfies `VectorStore` contract. | RET-002 |
| INF-004 | `LLMProvider` implementation | P0 | Hosted API or local LLM. | Satisfies `LLMProvider` contract. | None |
| INF-005 | `VLMProvider` implementation | P1 | Hosted API or local VLM. | Satisfies `VLMProvider` contract. | MM-001 |
| INF-006 | `PaperSource` implementation | P1 | arXiv API (candidate). | Satisfies `PaperSource` contract. | DISC-003 |
| INF-007 | PostgreSQL persistence for structured/metadata store | P1 | Papers, structured fields, relationships. | CRUD works for entities defined at the time. | UND-001 |
| INF-008 | Second implementation per interface | P2 | Swap validation for at least one interface. | Two implementations pass the same interface test suite. | Corresponding P0 item |
| INF-009 | Local model runtime support | P3 | Local inference as an LLM/VLM alternative. | TBD — deferred. | INF-004, INF-005 |

## DevOps

| ID | Title | Priority | Description | Acceptance criteria | Dependencies |
|---|---|---|---|---|---|
| DEVOPS-001 | `pyproject.toml` dependency/tooling setup | P0 | Single source of truth for dependencies, added incrementally per sprint. | Up to date with each sprint's actual dependencies. | None |
| DEVOPS-002 | `.env` / config management | P0 | Centralized settings/config loading; secrets via env vars. | No hard-coded secrets; config documented. | None |
| DEVOPS-003 | `docker-compose.yml` for local dev | P1 | App + vector DB + Postgres, filled in as each is actually needed. | Services start locally once populated (Sprint 2+). | INF-003, INF-007 |
| DEVOPS-004 | Test runner / CI-ready structure | P1 | Unit/integration/evaluation test layout runnable locally. | `pytest` (or equivalent) runs all three suites. | None |
| DEVOPS-005 | Logging/observability setup | P1 | Structured logging across ingestion/retrieval/understanding pipelines. | Log output includes stage/paper/page context per NFR-004. | None |
