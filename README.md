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

**Sprint 1 (Scientific Paper Ingestion) is implemented.** The full documentation set
below was written in Phase 0; Sprint 1 (defined in
[docs/implementation-plan.md](docs/implementation-plan.md)) has since built a PDF
ingestion pipeline — metadata, text, tables, figures, references, and page-level
evidence, for one PDF at a time, persisted as structured JSON (see "Ingestion Output
Layout" below). No retrieval, structured understanding, comparison, landscape, gap
analysis, or agent logic exists yet — see
[docs/decisions.md](docs/decisions.md) ADR-014 for what changed from the original
Sprint 1 plan (parser choice, a small domain-model addition) and why.

The pipeline has been validated with unit and integration tests (using PDFs generated
on the fly with PyMuPDF, not committed fixtures) but **not yet run against a real
curated AI/CV/ML paper collection** — see "Local Development" below for how to try it
against your own PDFs.

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
│   │   ├── models/          # Paper, Author, Page, TextBlock, Section, Figure, Table, Citation (implemented)
│   │   ├── schemas/         # Shared validation/serialization schemas (not yet needed — see below)
│   │   └── interfaces/      # DocumentParser (implemented); LLM/VLM/Embedding/VectorStore/PaperSource (future)
│   ├── ingestion/           # Ingestion orchestration: pipeline, assets, validation, persistence, report (implemented)
│   ├── infrastructure/
│   │   └── parsers/         # PyMuPDFDocumentParser + parsing heuristics (implemented)
│   ├── retrieval/           # Chunking, embedding, similarity search (supporting capability, Sprint 2+)
│   ├── multimodal/          # Figure/table understanding orchestration (supporting capability, Sprint 8)
│   ├── agent/                # (future) research workflow orchestration
│   ├── tools/                 # (future) agent-invocable capabilities
│   └── api/                   # FastAPI application (future)
│   # discovery/, understanding/, landscape/, comparison/, gap_analysis/, graph/
│   # are documented in architecture.md and created when their sprint begins —
│   # not scaffolded ahead of need.
├── tests/
│   ├── unit/                # Domain models, heuristics, pipeline orchestration (fake parser)
│   ├── integration/         # Real PyMuPDFDocumentParser + real pipeline against generated PDFs
│   └── evaluation/          # (future — Sprint 6+)
├── data/
│   ├── papers/
│   │   ├── raw/              # Local input PDFs you place here (gitignored)
│   │   └── processed/         # Ingestion output (gitignored — see "Ingestion Output Layout")
│   ├── figures/                # (unused by Sprint 1; figures live under papers/processed/<id>/figures/)
│   └── tables/                 # (unused by Sprint 1; tables live under papers/processed/<id>/tables/)
├── scripts/
│   └── ingest.py                # Sprint 1 CLI entry point
├── config/                       # Configuration files (not yet needed — no config exists yet)
├── pyproject.toml
├── docker-compose.yml
└── .gitignore
```

`src/domain/schemas` and `config/` remain empty (`.gitkeep` only) — Sprint 1 didn't
need them (see [docs/development-guidelines.md](docs/development-guidelines.md), "do
not over-engineer"). `retrieval/`, `multimodal/`, `agent/`, `tools/`, and `api/` are
scaffolded but still empty, reserved for their documented future sprints.

## Local Development

Sprint 1's ingestion pipeline is runnable locally. No API keys or `.env` file are
needed yet — nothing in Sprint 1 calls an external service.

```bash
python -m venv .venv
.venv/Scripts/activate       # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"

# Run the test suite (uses synthetically generated PDFs, no real papers needed):
pytest

# Ingest your own PDFs:
#   1. Place a few open-access PDFs (e.g. from arXiv — respect each paper's license/
#      terms) into data/papers/raw/ (gitignored, nothing there is committed).
#   2. Run:
python scripts/ingest.py
#   Output is written to data/papers/processed/<paper_id>/ (also gitignored — see
#   "Ingestion Output Layout" below) and a per-run summary prints to the console.
```

`docker-compose.yml` currently documents planned local services (Qdrant, PostgreSQL)
as comments; it will be filled in when those services are actually needed (Sprint 2).

## Ingestion Output Layout

Running `scripts/ingest.py` writes one directory per paper under
`data/papers/processed/` (structure as actually implemented — see
[docs/decisions.md](docs/decisions.md) ADR-014 for how/why this differs slightly from
the layout originally sketched for Sprint 1):

```
data/papers/processed/<paper_id>/
├── manifest.json          # IngestionReport (counts, warnings/errors) + file index
├── metadata.json          # title, authors, abstract, page_count, metadata_source
├── pages.json             # per-page text length / extraction-issue flags
├── text/
│   ├── blocks.json        # TextBlock[] — body text with page + reading-order provenance
│   └── sections.json      # Section[] — heuristically detected headings
├── figures/
│   ├── figures.json       # Figure[] — page, caption (if found), image_path, bbox
│   └── <figure_id>.<ext>  # the extracted image files themselves
├── tables/
│   └── tables.json        # Table[] — page, caption (if found), extracted rows
└── references/
    └── citations.json     # Citation[] — raw reference text, page, marker (if detected)
```

Neither `data/papers/raw/` nor `data/papers/processed/` are committed — raw papers may
be copyrighted, and processed output includes extracted paper text, which is a
redistribution of that same content in another form (see `.gitignore`).

## Contributing

This is currently a solo portfolio project in the planning stage. See
[docs/development-guidelines.md](docs/development-guidelines.md) for the coding
conventions that will apply once implementation starts.
