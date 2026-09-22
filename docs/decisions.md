# Architecture Decision Records

**Status:** Phase 0 — Planning
**Last updated:** 2026-09-22

This is an ADR log. Each record captures a decision made at a point in time, the
alternatives considered, and the consequences. Decisions here reflect the current plan,
not experimentally validated conclusions — no implementation exists yet, so no
technology choice below should be read as "proven best." Superseded decisions are marked
`[SUPERSEDED by ADR-XXX]` rather than deleted, to preserve history.

**Revision note (2026-09-22):** The product direction changed from a single-document
"PDF research assistant" to the Research Intelligence Platform (multi-paper analysis).
ADR-001–ADR-006 below are the original decisions, revised in place where the new
direction changed their reasoning; ADR-007 onward are new. None were deleted — see the
per-ADR notes for what changed and why.

---

## ADR-001: Use a Modular, Layered Architecture

**Status:** Accepted (unchanged by the product direction revision)

**Context:** The project spans several distinct concerns (discovery, parsing,
understanding, retrieval, landscape, comparison, gap analysis, graph, multimodal
inference, API) that are each likely to change independently as the project matures and
as better tools/models become available. A monolithic, tightly coupled implementation
would make later capabilities (multi-paper comparison, gap analysis, provider swaps)
costly to retrofit.

**Decision:** Adopt a layered architecture (API → application capabilities → domain
interfaces → infrastructure implementations) as described in `architecture.md`, with
dependencies pointing inward toward domain interfaces.

**Alternatives considered:**
- A single flat script/notebook-style implementation — rejected as unmaintainable beyond
  a quick prototype, and unsuitable for a portfolio project meant to demonstrate
  engineering practice.
- A microservices split (separate deployable services per layer) — rejected for MVP as
  unnecessary operational complexity for a solo developer; layers are logical/module-level
  for now, not separate services.

**Consequences:** More upfront structure/boilerplate than a quick script. Enables
independent testing and replacement of components per NFR-002/NFR-009. Requires
discipline (see `development-guidelines.md` module boundaries) to keep the dependency
direction intact as more capability modules (`discovery`, `understanding`, `landscape`,
`comparison`, `gap_analysis`, `graph`) are added.

---

## ADR-002: Keep the LLM Provider Replaceable

**Status:** Accepted (revised scope: LLM use is now understanding/comparison/gap-analysis
extraction and reasoning, not primarily chat)

**Context:** LLM APIs and local model runtimes change rapidly in capability, cost, and
availability. Coupling the codebase to one vendor's SDK would make future swaps (for
cost, capability, or offline/local operation — FR-107) expensive. Under the Research
Intelligence Platform direction, the LLM is used for structured field extraction
(Understanding), comparison synthesis, gap-hypothesis phrasing, and grounded Q&A — a
broader and more central role than the original single-document-chat scope, which makes
replaceability more important, not less.

**Decision:** Define an `LLMProvider` interface in `src/domain/interfaces`; all LLM
calls (extraction, comparison, gap hypotheses, grounded answers) go through this
interface. Concrete implementations live in `src/infrastructure`, selected via
configuration.

**Alternatives considered:**
- Calling a specific vendor SDK directly from application code — rejected; violates
  NFR-009 and would require rewrites to change providers.
- Using a heavyweight third-party abstraction framework as the *only* access path to
  LLMs — deferred; such frameworks may be used *inside* an infrastructure
  implementation, but the domain interface is owned by this project, not outsourced to a
  framework's abstraction.

**Consequences:** Slight indirection overhead. Enables testing application logic with a
fake `LLMProvider` (no real API calls needed for unit tests). No specific LLM vendor is
committed to yet; the first concrete implementation will be chosen during Sprint 3
(Understanding) based on practical constraints (cost, availability, structured-output
reliability) at that time.

---

## ADR-003: Keep the VLM Provider Replaceable — VLM Is a Supporting Capability

**Status:** Accepted (revised: VLM/multimodal understanding is explicitly repositioned
as a supporting capability, not a top-level product pillar)

**Context:** Vision-language model quality and cost vary significantly between vendors
and between hosted/local options. Figure/diagram/table understanding (FR-007/FR-008) is
expected to be the least mature part of the platform. Under the original direction,
figure analysis was one of the MVP's primary deliverables; under the Research
Intelligence Platform direction, it is a supporting capability invoked by Understanding
and Comparison when a structured field or comparison depends on visual content (see
`architecture.md` §0/§9), scheduled later (Sprint 8) so that the platform's core
multi-paper value does not depend on VLM maturity.

**Decision:** Define a `VLMProvider` interface in `src/domain/interfaces`, mirroring the
`LLMProvider` approach in ADR-002. All figure/table analysis in `src/multimodal` depends
only on this interface, and is invoked from other capabilities rather than exposed as a
standalone product surface.

**Alternatives considered:**
- Reusing the `LLMProvider` interface for VLM calls — rejected for now to keep
  text-generation and vision-understanding contracts independently evolvable; may be
  revisited once real implementations exist.
- Hard-coding a single VLM vendor — rejected per the same reasoning as ADR-002.
- Treating multimodal understanding as a Sprint 1–3 MVP deliverable (the original plan)
  — superseded; see ADR-011 for the explicit "RAG/VLM/agent are supporting technologies"
  decision this follows from.

**Consequences:** Same benefits/trade-offs as ADR-002, applied to the multimodal path.
No specific VLM vendor is committed to yet; chosen during Sprint 8, later than originally
planned.

---

## ADR-004: Keep the Vector Database Replaceable

**Status:** Accepted (unchanged by the product direction revision, beyond noting broader
use)

**Context:** Qdrant and pgvector (and others) offer different operational trade-offs. The
right choice may depend on factors only visible once real usage patterns (index size,
query load across a growing multi-paper collection) are observed. Retrieval now serves
Understanding and Comparison, not just direct user Q&A, so its interface needs to support
collection-scoped and paper-scoped queries (see `architecture.md` §8).

**Decision:** Define a `VectorStore` interface in `src/domain/interfaces` covering
upsert and similarity search with metadata filtering; `src/retrieval` depends only on
this interface. A concrete implementation (Qdrant, as the current candidate) is chosen
for Sprint 2, with the interface designed so pgvector or another store could be
substituted later.

**Alternatives considered:**
- Coupling retrieval logic directly to a specific vector DB's client/query API —
  rejected per NFR-009.
- Committing to pgvector immediately to avoid running a second storage service —
  deferred; Qdrant is kept as the initial candidate for its purpose-built vector search
  features, but this is not an experimentally validated choice, and pgvector remains a
  live alternative to reduce operational footprint if that becomes a priority.

**Consequences:** Retrieval logic is portable across vector stores. The specific choice
between Qdrant and pgvector should be revisited with real data once Sprint 2 is
underway, and that revisit should be recorded as a new ADR rather than silently changed.

---

## ADR-005: Scientific Papers (AI / Computer Vision / Machine Learning) as the Initial
Domain, and as First-Class Structured Domain Objects

**Status:** Accepted (revised: extended to make structured paper representations, not
just raw papers, first-class — see also ADR-008)

**Context:** The system needs a bounded initial domain to make parsing, extraction,
comparison, and evaluation tractable, and to keep the MVP realistic for a solo developer
(per `PRD.md`). AI/CV/ML papers are a domain the developer has direct familiarity with,
are available open-access (e.g. via arXiv), and share reasonably consistent structural
conventions (abstract, sections, figures, tables, references). Under the Research
Intelligence Platform direction, this decision also implies that the *structured
representation* of a paper (its extracted method, dataset, metrics, results) is as much
a first-class domain concern as the raw paper itself — see ADR-008.

**Decision:** Scope the MVP and initial evaluation corpus to AI/CV/ML research papers.
Architecture should not hard-code assumptions that make other scientific domains
impossible to support later (e.g. don't bake ML-specific vocabulary into parsing logic),
but broader domain generalization is explicitly a future capability to be evaluated, not
assumed to work.

**Alternatives considered:**
- A domain-agnostic "any PDF" scope from day one — rejected as too broad to build and
  evaluate meaningfully in early sprints; parsing/extraction/comparison quality would be
  hard to reason about across wildly different document structures.
- A narrower sub-domain (e.g. only computer vision papers) — considered unnecessarily
  restrictive without a specific reason to narrow further.

**Consequences:** Evaluation corpus and curated questions (Sprint 1+) are drawn from
AI/CV/ML papers. Claims about other domains (e.g. biology, physics papers) must not be
made until explicitly evaluated (see `PRD.md` Non-goals).

---

## ADR-006: Sequence Deterministic Pipelines Before Any Agentic Workflow

**Status:** Accepted (revised: broadened from "before agentic workflows" specifically to
the general principle that deterministic pipelines are preferred wherever sufficient —
see also ADR-012)

**Context:** Agentic tool-selection workflows (LangGraph or similar) are an attractive,
visible feature, but building them before the underlying capabilities (discovery,
ingestion, understanding, retrieval, comparison, landscape, gap analysis) exist as
solid, independently testable pipelines would mean the agent has nothing reliable to
orchestrate, and debugging failures would be ambiguous (bad pipeline vs. bad agent
decision). This reasoning strengthens, not weakens, under the Research Intelligence
Platform direction: there are now more distinct capabilities (eight sprints' worth) that
each need to be independently correct before an orchestration layer sits on top of them.

**Decision:** Sequence the roadmap so that Sprints 1–8 build and validate each
capability (ingestion, discovery/retrieval, understanding, landscape, comparison, gap
analysis, graph, multimodal) as fixed, deterministic pipelines. Dynamic agentic tool
selection is deferred to a future phase, once those capabilities are independently
proven (see `implementation-plan.md`).

**Alternatives considered:**
- Building the agent/orchestration layer first with stubbed capabilities — rejected;
  risks building orchestration logic around assumptions that don't match how real
  pipelines behave, and produces a demo that looks agentic but isn't grounded in working
  capabilities.
- Introducing the agent early "because this is an AI project" — explicitly rejected; see
  ADR-012, which generalizes this decision beyond just sequencing.

**Consequences:** The MVP (Sprints 1–3) and the subsequent differentiating sprints
(4–8) demonstrate evidence-grounded, cited, multi-paper analysis without "true" agentic
behavior — this is called out explicitly in `PRD.md` and `architecture.md` so it isn't
mistaken for the future agentic phase's capability. Tool interfaces (`src/tools`) are
only introduced alongside the agent layer itself, once there is something real to wrap.

---

## ADR-007: Research Intelligence (Multi-Paper Analysis) Is the Primary Product
Capability, Not Single-Document Q&A

**Status:** Accepted

**Context:** The project's original scope centered on "upload a PDF and ask questions."
That framing undersells the actual value: researchers already have ways to read a single
paper; what's hard is understanding a *field* — comparing methods, spotting common
datasets, noticing recurring limitations, and finding underexplored directions across
many papers. A generic PDF chatbot does not address this.

**Decision:** Reposition the product as a Research Intelligence Platform whose core unit
of intelligence is a collection of papers. Single-document retrieval/Q&A remains in the
system as a supporting capability (Retrieval, ADR intentionally not elevating it) that
Understanding and Comparison are built on, but it is not the top-level product loop or
the primary marketing/demo narrative. This reordering is reflected throughout
`PRD.md`, `architecture.md`, `implementation-plan.md`, and `product-backlog.md`.

**Alternatives considered:**
- Keep single-document Q&A as the primary deliverable and add multi-paper features
  later as an extension — rejected; this was the original plan, and it under-sells the
  differentiating value and risks the project reading as "yet another PDF chatbot" even
  after multi-paper features are added, since the architecture and demo narrative would
  still center on one document.
- Build both single- and multi-document flows as co-equal primary features from the
  start — rejected as unfocused for a solo developer; multi-paper analysis needs
  single-document extraction as a prerequisite anyway (Sprint 3 before Sprint 5), so
  there is no real parallel-track option without duplicating effort.

**Consequences:** Sprint sequencing, backlog priority order, and README/PRD framing all
lead with Discovery → Ingestion → Understanding → Comparison/Landscape/Gap Analysis, with
single-document Q&A demoted to "supporting capability" status throughout the
documentation (see the terminology sweep referenced in this file's revision note).

---

## ADR-008: Scientific Papers and Their Structured Representations Are First-Class
Domain Objects

**Status:** Accepted

**Context:** To compare papers, cluster them, or reason about gaps, the system needs
more than raw text — it needs comparable structured entities (Method, Dataset, Metric,
Experiment) extracted from each paper. If these are treated as transient LLM output
rather than first-class, persisted domain objects, every downstream capability
(Comparison, Landscape, Gap Analysis, Graph) would have to re-derive them, and evidence
traceability (ADR-009) would be much harder to maintain.

**Decision:** Model `Method`, `Dataset`, `Metric`, `Experiment`, `ResearchTopic`,
`ResearchClaim`, and `ResearchGapHypothesis` as domain entities in `src/domain/models`
(see `architecture.md` §7), populated by the Understanding pipeline (Sprint 3) and
persisted, not just produced ad hoc per request.

**Alternatives considered:**
- Treating structured extraction as a throwaway intermediate step recomputed per query —
  rejected; wastes LLM calls, and makes Comparison/Landscape/Gap Analysis dependent on
  in-request extraction quality/latency rather than a stable, inspectable store.
- Deferring structured domain modeling until Sprint 5 (Comparison) actually needs it —
  rejected; Understanding (Sprint 3) is explicitly the sprint that produces these
  entities, and defining them earlier (in documentation now, in code at Sprint 3) avoids
  a rework when Comparison/Landscape arrive.

**Consequences:** `src/domain/models` grows beyond the original ingestion-only entities
(Paper/Page/TextBlock/Table/Figure/Citation) to include these structured entities,
introduced specifically at Sprint 3, not scaffolded earlier than needed (see
`development-guidelines.md`).

---

## ADR-009: Important Claims Must Retain Traceable Evidence

**Status:** Accepted

**Context:** Any generated claim — a Q&A answer, an extracted method/dataset field, a
comparison cell, a landscape theme label, a gap hypothesis — is only as trustworthy as
its ability to be checked against the source papers. Without enforced evidence
traceability, the system could produce plausible-sounding but ungrounded output, which
is a worse failure mode for a research tool than an obviously wrong answer.

**Decision:** Every `ResearchClaim`-like output (see ADR-008) carries a pointer to the
specific paper/page/figure/table it was derived from (NFR-011). This is enforced at the
domain-model level (the field exists and is required), not left as a prompting
convention that can silently degrade.

**Alternatives considered:**
- Best-effort citations, added by prompting the LLM to "include a source" — rejected;
  without a structural requirement, missing or fabricated citations would be easy to
  ship unnoticed.
- Citing only at the paper level (not page/figure/table) — rejected as insufficiently
  precise for a tool whose value depends on being checkable; page-level (or finer)
  granularity is the minimum bar (see `requirements.md` FR-010).

**Consequences:** Every capability's output schema includes an evidence-pointer field.
Evaluation (`evaluation.md`) treats "evidence coverage" and "evidence correctness" as
first-class metrics across Understanding, Comparison, and Gap Analysis, not just for
basic Q&A.

---

## ADR-010: AI-Generated Research Gaps Are Hypotheses Supported by Evidence, Not
Guaranteed Facts

**Status:** Accepted

**Context:** Gap analysis (Sprint 6) is the capability most prone to overreach: a
clustering or statistical pattern (e.g. "few papers evaluate X") can look like a
confident discovery when it is really an artifact of a small, non-exhaustive collection.
Presenting such output as a settled fact would be actively misleading to a researcher
relying on it.

**Decision:** Every gap-analysis output is framed as a hypothesis, explicitly stating
the supporting evidence count and the list of supporting papers (FR-061, NFR-012), using
language like "potential research gap identified: N of M analyzed papers..." rather than
"this is a research gap." This framing requirement is enforced as a functional
requirement, not left to prompt wording alone, and is checked by the "false-positive gap
rate" and "evidence coverage/correctness" metrics in `evaluation.md`.

**Alternatives considered:**
- Presenting gap output as direct findings (as in the original PDF-assistant framing,
  which had no gap-analysis capability at all and so never faced this question) —
  rejected once gap analysis was added to the roadmap, precisely because the risk of
  overclaiming is highest here.
- Suppressing gap analysis entirely to avoid the risk — rejected; the capability is
  valuable when correctly hedged, and `PRD.md`/`requirements.md` treat correct hedging
  as a hard requirement rather than avoiding the feature.

**Consequences:** UI/API copy, not just internal data structures, must reflect this
framing — this is a product-level constraint, not only a backend one. `PRD.md` Non-goals
explicitly calls out presenting gaps as fact as out of scope/forbidden behavior.

---

## ADR-011: RAG, VLMs, and Agents Are Supporting Technologies, Not the Product
Definition

**Status:** Accepted

**Context:** It would be easy to let the architecture be organized around "we use RAG"
and "we use a VLM" and "we use an agent," since those are the trendy building blocks.
But the product's value comes from what it produces (structured, comparable,
evidence-linked research knowledge across a paper collection), not from which AI
techniques it happens to use to produce it. Organizing the architecture around
techniques rather than capabilities was a risk in the original single-document-chatbot
framing, where RAG effectively *was* the product.

**Decision:** The architecture (`architecture.md` §0) is organized around the
conceptual capability workflow (Discovery → Ingestion → Understanding → Landscape →
Comparison → Gap Analysis → Graph), with RAG, VLM, and agentic orchestration positioned
as supporting technologies used only where they demonstrably help: RAG for evidence
retrieval underlying Understanding/Comparison/Q&A; VLM for figure/diagram/table
understanding (ADR-003); agents for future multi-step workflow automation (ADR-006,
ADR-012).

**Alternatives considered:**
- Organizing `src/` around techniques (a `rag/` module, an `agent/` module as the top
  layer) — rejected; this is close to what the original plan did, and it obscures the
  actual product capabilities being delivered.
- Avoiding these techniques' names in the architecture entirely — rejected as
  impractical; they are real, named components (see `architecture.md` §8's interface
  table), just not the organizing principle.

**Consequences:** `src/` is organized by capability (`discovery`, `ingestion`,
`understanding`, `retrieval`, `landscape`, `comparison`, `gap_analysis`, `graph`,
`multimodal`, `agent`), matching `architecture.md` §3, rather than by AI technique.

---

## ADR-012: Prefer Deterministic Pipelines Over Agents; Do Not Add an Agent Just Because
This Is an AI Project

**Status:** Accepted

**Context:** This generalizes ADR-006's sequencing decision into a standing engineering
principle, because the temptation to reach for an agent framework recurs at every
sprint, not just at the start.

**Decision:** Default to deterministic pipelines (fixed sequences of steps, as described
per-sprint in `implementation-plan.md`) for every capability. Introduce agentic
(dynamic tool-selection) behavior only where a capability genuinely requires
runtime-variable multi-step reasoning that a fixed pipeline cannot express, and only
after that capability's building blocks already work deterministically (ADR-006).

**Alternatives considered:**
- Using an agent framework as the default orchestration mechanism for every capability
  — rejected; adds non-determinism, latency, and debugging difficulty (per
  `evaluation.md` Agent metrics: unnecessary tool calls, latency) where a fixed pipeline
  would be simpler, cheaper, and easier to evaluate.

**Consequences:** `src/agent` and `src/tools` remain unpopulated until a specific,
justified need arises (see `implementation-plan.md` "Future" phase). This is also a
`development-guidelines.md` rule: do not add abstractions or orchestration machinery
ahead of a proven need.

---

## ADR-013: The Core Domain Must Not Depend Directly on One Paper Data Source

**Status:** Accepted

**Context:** The MVP starts with a manually curated paper collection (no crawling,
per `PRD.md` constraints), but Discovery (Sprint 2+) is expected to eventually search
external sources (e.g. arXiv). Coupling ingestion/discovery logic directly to one
source's API would make it hard to add a second source or to swap sources if terms of
service or API availability change.

**Decision:** Define a `PaperSource` interface in `src/domain/interfaces` (see
`architecture.md` §8), with `src/discovery` depending only on this interface. The MVP's
"manual collection input" (FR-020) is itself treated as a trivial `PaperSource`
implementation (a static list), so the same interface covers both the MVP and future
automated-search implementations without a later rewrite.

**Alternatives considered:**
- Hard-coding arXiv-specific logic into `src/discovery` from the start — rejected per
  NFR-009's general provider-replaceability principle, applied here to data sources
  rather than model/storage providers.
- Deferring the interface until Sprint 2 actually needs external search — considered,
  but rejected in favor of defining the interface now (documentation-only, Phase 0) and
  implementing the trivial manual-input case against it from Sprint 1, so the seam
  exists from the first real usage rather than being retrofitted.

**Consequences:** `src/discovery`'s manual-collection-input code (Sprint 1/2) and any
future arXiv-search code (Sprint 2+) both implement `PaperSource`, validating the
interface's replaceability the same way ADR-002/ADR-003/ADR-004 do for model/storage
providers.

---

## ADR-014: Sprint 1 Parser Choice (PyMuPDF) and Domain-Model Adjustments

**Status:** Accepted

**Context:** `implementation-plan.md`'s original Sprint 1 scope named Docling as the
candidate `DocumentParser` implementation, with PyMuPDF as a fallback "if Docling
proves difficult to integrate." Docling depends on a full ML-based layout/table model
stack (torch, transformers, and their own dependency trees), which is a large
dependency footprint for a sprint whose stated goal is a *reliable ingestion
pipeline*, not the most accurate possible layout model — and
`development-guidelines.md`'s Dependency Management rule says to choose the smallest
reasonable dependency set for the current phase's actual work. Separately, while
implementing Sprint 1, three small gaps appeared between the previously-documented
domain model and what the ingestion pipeline actually needed to produce.

**Decision:**
1. **Parser:** Implement `DocumentParser` with PyMuPDF (`pymupdf`) as the sole Sprint 1
   parser, not Docling. PyMuPDF is a mature, lightweight library (no ML runtime
   dependency) that provides everything Sprint 1's scope requires: page-level text
   with bounding boxes, embedded image extraction, a built-in ruled-table finder
   (`Page.find_tables`), and PDF metadata access. This is an initial-implementation
   choice, not a claim that PyMuPDF is categorically better than Docling — Docling
   (or another parser) remains a live candidate for the swappability validation work
   in ING-010/backlog, and nothing in the `DocumentParser` interface (defined before
   this choice was made) had to change to accommodate this decision, which is itself
   a small positive validation of the interface's design.
2. **Section as a Sprint 1 entity:** Add `Section` (heuristically detected heading:
   title, page, order) to Sprint 1's domain models, alongside `Paper`, `Page`,
   `TextBlock`, `Table`, `Figure`, `Citation`, and `Author`. The original
   `implementation-plan.md` Sprint 1 model list did not name `Section` explicitly,
   but FR/scope text always called for "sections where reliably detectable," and
   deferring a dedicated entity for it would have meant burying heading information
   as unstructured text inside `TextBlock`, which is unrecoverable later without
   re-parsing.
3. **Citation, not "Reference":** The entity introduced in `architecture.md` §7.1 as
   `Citation` is implemented under that name, even though Sprint 1's brief also uses
   "Reference" for the same concept informally. Keeping one name avoids two labels for
   one domain object.
4. **Output layout — small deviation from the sketch:** The persisted output groups
   text blocks and sections under `text/` as `blocks.json`/`sections.json` (rather
   than one file per block), adds a top-level `pages.json` for page-level metadata
   (`Page` didn't have an obvious home in the originally sketched layout), and stores
   citations under `references/citations.json`. This is documented in full in
   `README.md`'s "Ingestion Output Layout" section, per the Sprint 1 brief's
   instruction to document the final structure rather than force the sketched one.

**Alternatives considered:**
- Implementing both Docling and PyMuPDF in Sprint 1 to compare — rejected;
  `development-guidelines.md` and the Sprint 1 brief both say choose one initial
  implementation and defer a second to the explicit swappability-validation backlog
  item (ING-010), not build two in parallel from the start.
- Leaving `Section` out of Sprint 1 and adding it only when Landscape/Understanding
  (Sprint 3+) need it — rejected; heading locations are cheap to capture during
  parsing and expensive to reconstruct later from persisted `TextBlock`s alone, and
  Sprint 1's own scope ("sections where reliably detectable") already implied it.

**Consequences:** `pyproject.toml` gains `pymupdf` and `pydantic` as runtime
dependencies and `pytest` as a dev dependency — still zero RAG/embedding/vector-store/
LLM/VLM dependencies, consistent with Sprint 1's scope. A second `DocumentParser`
implementation (ING-010) remains future work, not done in this sprint. Known,
documented extraction limitations of the PyMuPDF implementation (vector-drawn figures
not captured, borderless tables missed, heading/reference-splitting heuristics can
misfire on unconventional layouts) are recorded in
`src/infrastructure/parsers/pymupdf_parser.py`'s module docstring and repeated in this
session's final report — Sprint 1's goal was a *reliable, honestly-reported* pipeline,
not a claim of high extraction accuracy (see `evaluation.md`).

---

## ADR-015: Sprint 2 Retrieval-Stack Choices (fastembed, qdrant-client local mode, Chunk)

**Status:** Accepted

**Context:** ADR-004 named Qdrant as a "candidate" `VectorStore` implementation, not a
validated choice, and explicitly said the choice "should be revisited with real data
once Sprint 2 is underway, and that revisit should be recorded as a new ADR rather
than silently changed" — this ADR is that revisit. Similarly, `architecture.md` §2.3
lists "BGE / Jina" as `EmbeddingProvider` candidates without commitment. Sprint 2's
actual scope (a small, manually curated local collection, per `PRD.md`'s MVP framing)
makes a full Qdrant server + Docker Compose service disproportionate, and a
torch-based embedding stack (sentence-transformers) disproportionate to
`development-guidelines.md`'s "smallest reasonable dependency set" rule — the same
reasoning ADR-014 used to pick PyMuPDF over Docling in Sprint 1. Separately, while
implementing retrieval, `TextBlock` (Sprint 1) proved insufficient as the unit to
embed/store directly: it carries no `paper_id` (only meaningful nested inside a
`Paper`), and the `VectorStore` payload needs a self-contained evidence unit.

**Decision:**
1. **VectorStore**: use `qdrant-client`'s embedded/local on-disk mode
   (`QdrantClient(path=...)`), not a Qdrant server. Confirmed by direct testing that
   local mode implements the same payload-filtering API (`Filter`/`FieldCondition`/
   `MatchAny`) as server mode — the same underlying engine, exposed identically — so
   RET-002's paper-scoped-filtering requirement is met without any operational
   service. Data lives under `data/index/` (gitignored, mirroring
   `data/papers/processed/`'s pattern).
2. **EmbeddingProvider**: use `fastembed` with `BAAI/bge-small-en-v1.5` — an
   ONNX-runtime-based library with no torch/sentence-transformers dependency tree
   (confirmed: `pip install fastembed qdrant-client` pulled in `onnxruntime`, not
   `torch` or `transformers`), a small model (~130MB), CPU-friendly.
3. **`Chunk`** added as a new domain model (`src/domain/models/chunk.py`), parallel
   to how ADR-014 added `Section` mid-Sprint-1: a retrievable-evidence-unit concept
   needed by the `VectorStore` interface's payload shape (`chunk_id`, `paper_id`,
   `page`, `text`, `source_block_id` tracing back to the originating `TextBlock` for
   evidence traceability, ADR-009) and reused unmodified by Sprint 3's Understanding,
   not an implementation detail of one infrastructure provider.

**Alternatives considered:**
- A full Qdrant server via `docker-compose.yml` (already scaffolded with a
  placeholder per DEVOPS-003) — deferred; adds an operational dependency (a running
  service) this sprint's scope doesn't need, and local mode's API is close enough to
  server mode that migrating later is a configuration change, not a rewrite.
- pgvector — deferred per ADR-004's original reasoning, unchanged; remains a live
  alternative if `data/index/`'s local-mode footprint or PostgreSQL consolidation
  becomes a priority later.
- sentence-transformers/torch-based embeddings — rejected for the same
  dependency-footprint reason ADR-014 rejected Docling.
- Operating directly on `TextBlock` without a `Chunk` model — rejected because
  `TextBlock` lacks `paper_id`, and folding chunking-splitting concerns into a
  Sprint-1 model would blur its meaning for a Sprint-2-specific need.
- Qdrant point ids as raw `chunk_id` strings — rejected; Qdrant requires int/UUID
  ids. Resolved via a deterministic `uuid.uuid5(chunk_id)` as the point id, with the
  human-readable `chunk_id` kept in the payload and returned from `query()` — so
  callers never see an opaque UUID.

**Consequences:** `pyproject.toml` gains `fastembed` and `qdrant-client`; still zero
LLM/VLM dependencies (Sprint 3 concern, per RET-007's narrow no-generation
interpretation this sprint — see `implementation-plan.md`'s Sprint 2 status note).
`docker-compose.yml`'s vector-DB placeholder stays unfilled this sprint (no server to
run) — DEVOPS-003 remains open/future. Re-embedding an existing collection with a
different model requires clearing `data/index/` — `QdrantLocalVectorStore` raises
`VectorStoreError` on a dimension mismatch rather than silently creating an
incompatible collection or corrupting the existing one. If corpus size or concurrent-
query load later justify a server, that is a new ADR, not a silent change (mirroring
ADR-004's own instruction to itself).

---

## Template for Future ADRs

```
## ADR-XXX: <Title>

**Status:** Proposed | Accepted | Superseded by ADR-YYY

**Context:** <What situation/problem prompted this decision?>

**Decision:** <What was decided?>

**Alternatives considered:** <What else was considered, and why not chosen?>

**Consequences:** <What does this make easier/harder? What follow-up is implied?>
```
