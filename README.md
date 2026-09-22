# Research Intelligence Platform

**Status: Planning / Phase 0.** No application functionality is implemented yet.
This repository currently contains project planning, architecture documentation, and
initial repository scaffolding only.

## Problem

Scientific literature is large, fragmented, and difficult to analyze across many
papers. Finding papers is only the beginning — understanding a research field means
comparing methods, datasets, and results across dozens of papers, noticing which
limitations keep recurring, and spotting where a direction is underexplored. Doing this
by hand is slow, and generic "chat with a single PDF" tools don't help, because they
answer questions about one document, not about a body of literature.

## What This Is

Research Intelligence Platform transforms a **collection** of scientific papers into
structured, searchable, evidence-backed research intelligence: per-paper structured
knowledge (problem, method, dataset, metrics, results, limitations), multi-paper
comparison, a clustered research landscape view, and evidence-based research-gap
hypotheses — every claim traceable back to the specific paper and page it came from.

**This is explicitly not:**
- A ChatGPT-style "paste a paper, ask questions" tool.
- A generic RAG chatbot wrapped around a PDF.
- A generic paper summarizer.

Retrieval-augmented generation (RAG), vision-language models (VLMs), and agentic
workflows are used *inside* the platform where they add clear value (grounded evidence
retrieval; figure/diagram/table understanding; later, multi-step workflow automation) —
they are supporting technologies, not the product itself. The core unit of intelligence
is the collection of papers, not a single document. See
[docs/decisions.md](docs/decisions.md) (ADR-007, ADR-011) for the reasoning.

## Target Users

Researchers, students, engineers, and other technical professionals who need to
investigate a research field — not just read one paper, but understand how a body of
work relates: which methods are used, which datasets and metrics are standard, which
limitations recur, and where the literature is thin.

## Current Status

Phase 0 — Planning. The full documentation set below has been written; implementation
has not started. Sprint 1 (defined in
[docs/implementation-plan.md](docs/implementation-plan.md)) will build a scientific
paper ingestion pipeline (metadata, text, tables, figures, references, page-level
evidence) for a small manually curated paper collection — no retrieval, structured
understanding, comparison, landscape, gap analysis, or agent logic yet.

## Documentation

| Document | Contents |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Product overview, problem statement, users, goals/non-goals, MVP definition, success criteria |
| [docs/requirements.md](docs/requirements.md) | Functional and non-functional requirements (FR-/NFR- IDs), grouped by capability area |
| [docs/architecture.md](docs/architecture.md) | System architecture, layering, data flow, domain model, provider-replaceability design (with diagrams) |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Phased roadmap (Sprints 1–8 + future) and detailed Sprint 1 plan |
| [docs/product-backlog.md](docs/product-backlog.md) | Prioritized backlog (P0–P3), grouped by capability area, with acceptance criteria |
| [docs/evaluation.md](docs/evaluation.md) | Evaluation strategy: discovery, extraction, retrieval, generation, multimodal, clustering, comparison, and gap-analysis metrics — clearly marked planned vs. implemented vs. experimental |
| [docs/development-guidelines.md](docs/development-guidelines.md) | Coding standards, module boundaries, provider-abstraction rules, "deterministic pipelines over agents" principle |
| [docs/decisions.md](docs/decisions.md) | Architecture Decision Records (ADRs), including the product-direction revision to Research Intelligence Platform |

## Core Workflow (Conceptual)

```
Paper Sources → Discovery → Ingestion → Paper Understanding → Research Landscape
              → Paper Comparison → Evidence-Based Gap Analysis → Research Graph
```

Multimodal (VLM) understanding and agentic orchestration support this workflow where
needed, rather than sitting at its center. Full detail and diagrams:
[docs/architecture.md](docs/architecture.md).

## Planned Architecture

Layered, with dependencies pointing inward toward domain interfaces — application logic
never depends on a specific vendor SDK or a specific paper data source directly:

```
User → API → Application Capabilities (discovery, ingestion, understanding, retrieval,
              landscape, comparison, gap_analysis, graph, multimodal, [future] agent)
       → Domain Interfaces → Infrastructure Implementations
```

Domain interfaces (`LLMProvider`, `VLMProvider`, `EmbeddingProvider`, `VectorStore`,
`DocumentParser`, `PaperSource`) are defined once and can each be implemented by
multiple providers, selected via configuration. Full detail and diagrams:
[docs/architecture.md](docs/architecture.md).

## Planned Stack (Candidates — Not Final Commitments)

These are starting candidates, chosen for prototyping speed; the architecture is designed
so each can be replaced without touching domain/application logic (see
[docs/decisions.md](docs/decisions.md)).

- **Language/API:** Python, FastAPI
- **Agent orchestration:** LangGraph (future, optional — after deterministic pipelines exist)
- **Parsing:** Docling (candidate), PyMuPDF (fallback candidate)
- **Embeddings / reranking:** BGE or Jina
- **Vector database:** Qdrant (candidate), pgvector (alternative)
- **Relational/structured storage:** PostgreSQL
- **LLM / VLM:** hosted API and/or local model, provider-agnostic via interfaces
- **Paper source (future):** arXiv API (candidate)
- **Frontend (post-MVP):** React + Tailwind
- **Local dev orchestration:** Docker Compose

## Development Roadmap

See [docs/implementation-plan.md](docs/implementation-plan.md) for full detail.

| Sprint | Focus |
|---|---|
| Phase 0 | Planning (this stage) |
| Sprint 1 | Scientific paper ingestion (text/tables/figures/references/metadata) — **current target** |
| Sprint 2 | Paper discovery (curated collection input) and retrieval |
| Sprint 3 | Structured paper understanding (problem/method/dataset/metric/result/limitation) — completes the MVP |
| Sprint 4 | Research landscape and clustering |
| Sprint 5 | Multi-paper comparison |
| Sprint 6 | Evidence-based research gap analysis |
| Sprint 7 | Research graph |
| Sprint 8 | Multimodal (VLM) paper understanding |
| Future | Research workflow automation and agentic capabilities |

## Repository Structure

```
research-intelligence-platform/
├── docs/                    # Planning and technical documentation
├── src/
│   ├── domain/
│   │   ├── models/          # Core entities (Paper, Method, Dataset, Metric, ...)
│   │   ├── schemas/         # Shared validation/serialization schemas
│   │   └── interfaces/      # Provider-agnostic contracts (LLM, VLM, Embedding, VectorStore, Parser, PaperSource)
│   ├── ingestion/           # PDF parsing orchestration
│   ├── retrieval/           # Chunking, embedding, similarity search (supporting capability)
│   ├── multimodal/          # Figure/table understanding orchestration (supporting capability)
│   ├── agent/                # (future) research workflow orchestration
│   ├── tools/                 # (future) agent-invocable capabilities
│   ├── infrastructure/        # Concrete provider implementations
│   └── api/                   # FastAPI application
│   # discovery/, understanding/, landscape/, comparison/, gap_analysis/, graph/
│   # are documented in architecture.md and created when their sprint begins —
│   # not scaffolded ahead of need.
├── tests/
│   ├── unit/
│   ├── integration/
│   └── evaluation/
├── data/
│   ├── papers/               # Local sample PDFs (gitignored)
│   ├── figures/                # Extracted figure images (gitignored)
│   └── tables/                 # Extracted table data (gitignored)
├── scripts/                    # Local dev / ingestion entry-point scripts
├── config/                     # Configuration files
├── pyproject.toml
├── docker-compose.yml
└── .gitignore
```

Some directories from the platform's original single-document-focused plan
(`retrieval/`, `multimodal/`, `agent/`, `tools/`) are already scaffolded; they remain
valid under the revised direction as supporting/future capabilities (see
[docs/decisions.md](docs/decisions.md)). No source files have been added to any
directory yet — only `.gitkeep` placeholders — per the Phase 0 constraint of
documentation/scaffolding only.

## Local Development

Not yet applicable — no runnable code exists. Once Sprint 1 begins:

1. Python 3.11+ will be required (see `pyproject.toml`).
2. Dependencies will be added incrementally per sprint (not pre-installed speculatively —
   see [docs/development-guidelines.md](docs/development-guidelines.md)).
3. `docker-compose.yml` currently documents planned local services (Qdrant, PostgreSQL)
   as comments; it will be filled in when those services are actually needed (Sprint 2).
4. Secrets/config will be supplied via a local `.env` file (never committed); an
   `.env.example` will be added once real configuration variables exist.

This section will be updated as soon as there's something runnable.

## Contributing

This is currently a solo portfolio project in the planning stage. See
[docs/development-guidelines.md](docs/development-guidelines.md) for the coding
conventions that will apply once implementation starts.
