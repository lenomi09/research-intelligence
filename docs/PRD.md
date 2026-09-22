# Product Requirements Document (PRD)

**Project:** Research Intelligence Platform
**Status:** Phase 0 — Planning
**Last updated:** 2026-09-22

## Product Overview

Research Intelligence Platform is a portfolio project that transforms a collection of
scientific papers into structured, searchable, evidence-backed research intelligence.
It ingests papers (text, tables, figures, references), extracts structured knowledge
about each one (problem, method, dataset, metrics, results, limitations), and reasons
about **relationships across the collection**: how methods differ, which datasets and
metrics are common, which limitations recur, and where the literature is thin.

The core unit of intelligence is the **collection of papers**, not a single document.
Retrieval-augmented generation (RAG), vision-language models (VLMs), and agentic
workflows are supporting technologies used where they add clear value (grounded
evidence retrieval, figure/diagram/table understanding, future multi-step workflows) —
they are not the product definition. The system is built incrementally with a strong
emphasis on modular architecture, provider independence, evidence traceability, and
evaluation-driven development.

## Problem Statement

Researchers face a large and continuously growing body of scientific literature. Finding
papers is only the beginning. Understanding a research field requires organizing papers
by topic and method, comparing experimental setups and results across many papers,
tracking which datasets and metrics are standard, noticing which limitations keep
recurring, and spotting where a direction is underexplored. Doing this manually across
dozens of papers is slow and error-prone, and generic "chat with a single PDF" tools do
not help — they answer questions about one document, not about a body of literature.

## User Problem

A researcher, student, or engineer investigating a research field wants to:
- Understand what has already been tried across many papers, not re-read each one in full.
- Compare papers by method, dataset, metric, and result, with the comparison traceable
  back to the specific paper and location it came from.
- See the shape of a research direction: dominant methods, common datasets, emerging
  themes, and recurring limitations.
- Get a starting hypothesis about underexplored combinations or gaps — clearly labeled
  as a hypothesis supported by evidence, not an unquestionable fact.

## Target Users

- **Primary (MVP):** the developer themselves, and technically literate users
  (ML/CV/AI researchers, grad students, engineers) surveying a research area, demoing
  the project as a portfolio piece.
- **Secondary (future):** researchers in adjacent scientific domains, once domain
  generalization has been evaluated (see [Non-goals](#non-goals)).

## Use Cases

1. Ingest a small collection of AI/CV/ML papers and extract structured metadata,
   methods, datasets, metrics, and results for each.
2. Ask a factual question about a specific paper, answered from retrieved text with a
   page citation (supporting capability, not the product's primary value).
3. Compare 2+ papers by method, dataset, metric, and reported result, with each claim
   traceable to its source paper/page.
4. Browse a research landscape view: papers grouped by theme/method, showing how a
   direction has evolved.
5. Review a candidate research gap hypothesis (e.g. "only 3 of 120 analyzed papers
   evaluate cross-domain generalization"), with the supporting papers listed as evidence.
6. Ask a question that requires reading a specific figure or table (VLM-assisted,
   supporting capability).
7. (Future) Explore a research graph: paper-to-paper, paper-to-method, paper-to-dataset
   relationships.
8. (Future) Automated multi-step literature investigation via an agentic workflow.

## Goals

- Deliver an MVP that ingests a small collection of scientific papers and produces
  structured, evidence-linked knowledge about each (Discovery/Ingestion/Understanding),
  as the foundation for cross-paper analysis.
- Demonstrate multi-paper comparison with traceable evidence as the platform's
  differentiating capability, not single-document Q&A.
- Demonstrate a modular, provider-independent architecture (LLM/VLM/embeddings/vector
  store/parser/paper-source can be swapped via configuration, not code rewrites).
- Treat research-gap and landscape outputs as evidence-supported hypotheses, never as
  presented facts, and say so explicitly in the product's own output.
- Establish an evaluation methodology from the start, even if initial metrics are
  qualitative/manual, and clearly separate planned, implemented, and experimentally
  measured evaluation.

## Non-goals

- Being a generic "chat with PDF" product — single-document Q&A is a supporting
  capability, not the product's value proposition (see `architecture.md` for how this
  shapes prioritization).
- Supporting every scientific domain from day one (initial domain is AI/CV/ML papers;
  broader domain generalization is a future capability that must be evaluated, not
  assumed).
- Building a production SaaS with multi-tenant auth, billing, or horizontal scaling.
- Achieving state-of-the-art benchmark scores — this is not a research paper.
- Presenting AI-identified research gaps as validated conclusions rather than
  evidence-supported hypotheses for a human to evaluate.
- Automated large-scale paper crawling/discovery at MVP stage (see Scope).
- Mobile apps.

## MVP Definition

The MVP (see `implementation-plan.md`, Sprints 1–3) supports, for a small manually
curated collection of papers:

1. Paper ingestion: parse PDFs into text, tables, figures, references, and page-level
   metadata (Sprint 1).
2. Paper discovery/retrieval: search and retrieve relevant text evidence across the
   collection (Sprint 2).
3. Structured paper understanding: extract research problem, methodology, dataset,
   metrics, and results per paper, with evidence pointers (Sprint 3).
4. Grounded question answering over one or more papers, with citations (built on the
   above, not the primary deliverable in isolation).

Multi-paper comparison, research landscape clustering, gap-hypothesis generation, and
the research graph are explicitly **post-MVP** (Sprints 4–7) — see Scope below. The MVP
is intentionally scoped to a **small, manually curated paper collection**, a **single
research domain**, and a **local/single-user deployment**, running via Docker Compose.

## Future Vision

Beyond the MVP, the platform builds toward the full conceptual workflow: automated paper
discovery from external sources, a clustered research landscape view, structured
multi-paper comparison, evidence-based gap hypotheses, and a research graph relating
papers, methods, datasets, and authors. Later still, an agentic layer could automate
multi-step literature investigation (e.g. "survey this subfield and summarize open
problems") on top of the deterministic pipelines built earlier. See
`implementation-plan.md` for sequencing; none of this is a commitment and will be
re-scoped based on what is learned building the MVP.

## Scope

**In scope (MVP, Sprints 1–3):**
- Paper ingestion: text, table, figure, reference/citation extraction with page-level
  provenance, for a small manually assembled collection (no crawling).
- Retrieval of relevant evidence across the collection.
- Structured extraction of research problem, methodology, dataset, metrics, and results
  per paper, each retaining a pointer back to its source evidence.
- Grounded question answering (single- or multi-paper) with citations, as a supporting
  capability built on the above.

**In scope (post-MVP, sequenced later — see `implementation-plan.md`):**
- Automated paper discovery from external sources (e.g. arXiv search) with ranking,
  deduplication, and filtering.
- Multi-paper structured comparison (method/dataset/metric/result/limitation).
- Research landscape clustering (themes, emerging topics, method/dataset relationships).
- Evidence-based research gap hypotheses.
- Research graph (paper–paper, paper–method, paper–dataset, paper–author relationships).
- Deeper multimodal (VLM) understanding of figures/diagrams/charts.
- Agentic, multi-step research workflows.
- A usable frontend (React + Tailwind, candidate).
- Formal evaluation harness with a benchmark dataset.

## Out of Scope

- Non-PDF input formats (e.g. HTML papers, LaTeX source) in the MVP.
- Non-English papers in the MVP.
- Fine-tuning any models.
- Handwriting/scanned-image (non-digital-native) PDFs in the MVP — OCR quality for
  scanned documents is a future evaluation item, not an MVP guarantee.
- Authentication, multi-tenancy, and billing.
- Large-scale automated paper crawling at MVP stage (a small, manually curated
  collection is used instead).
- Presenting clustering/gap-analysis output as fact rather than as a hypothesis with
  cited supporting evidence (see ADR on this in `decisions.md`).

## Assumptions

- Input PDFs are digital-native (text-selectable), not scanned images, for the MVP.
- Papers are primarily in AI / Computer Vision / Machine Learning, using conventional
  academic layout (single/double column, labeled figures, tables, and references).
- Development and initial evaluation happen locally or on a single developer machine,
  with access to at least one hosted LLM/VLM API and/or a local model runtime.
- The developer is the primary evaluator during MVP development (no dedicated QA team
  or domain-expert panel, though expert relevance review is a desired future evaluation
  input for gap hypotheses — see `evaluation.md`).

## Constraints

- Solo developer, part-time effort — scope must stay realistic per sprint.
- No committed budget for paid APIs beyond modest personal spend; local model fallback
  should remain architecturally possible (see `decisions.md`).
- No access to proprietary/licensed paper corpora; must rely on open-access papers
  (e.g. arXiv) for development and evaluation data.
- No automated large-scale crawling at MVP stage — a small, manually curated collection
  keeps ingestion, extraction, and evaluation tractable for a solo developer.

## Risks

- **Parsing quality risk:** scientific PDF layouts (multi-column, inline figures/tables,
  reference formatting) are hard to parse reliably; poor parsing degrades every
  downstream capability, including structured extraction and comparison.
- **Extraction accuracy risk:** structured field extraction (method, dataset, metric,
  result) from free text is harder and less mature than simple text retrieval; errors
  here propagate into comparison and landscape views.
- **Grounding/hallucination risk:** LLMs may produce claims, comparisons, or citations
  that don't match the source evidence; requires explicit verification, not just
  prompting (see evidence-traceability ADR in `decisions.md`).
- **Gap-hypothesis overreach risk:** presenting a clustering/statistical pattern as a
  confirmed research gap rather than a hypothesis would be actively misleading; the
  product must always frame these as evidence-supported hypotheses (see `PRD.md`
  Non-goals and `decisions.md`).
- **Multimodal accuracy risk:** VLM figure/table understanding is less mature than text
  understanding; it is scoped as a supporting capability so its weaknesses don't block
  the core product value.
- **Scope creep risk:** landscape, comparison, gap-analysis, graph, and agentic
  capabilities are individually attractive to build early; must be sequenced after a
  solid ingestion + retrieval + understanding foundation (see `implementation-plan.md`).
- **Provider/source lock-in risk:** without enforced interfaces, convenience will pull
  implementation toward a single vendor's SDK idioms or a single paper-source API.
- **Evaluation risk:** without ground-truth extraction/comparison labels, "correctness"
  is subjective; must build even a small labeled set early (see `evaluation.md`).

## Success Criteria

MVP is considered successful when, for a small set (10–20) of manually curated AI/CV/ML
papers:
- The system correctly parses text, references, and the majority of tables and figures
  (measured manually against the source PDFs).
- The system correctly extracts structured fields (problem, method, dataset, metrics)
  for the majority of the collection, judged against manual annotation.
- The system answers a manually curated set of text-based and simple comparison
  questions with retrieved evidence that a human judges as relevant and faithful.
- Every generated claim, answer, or comparison includes a citation traceable to a
  specific paper and page.
- Any one of {LLM, VLM, embedding model, vector store, parser, paper source} can be
  swapped via configuration/implementation change without modifying domain or
  application logic.
