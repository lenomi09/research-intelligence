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

**Sprints 1 and 2 (Ingestion; Discovery and Retrieval) are implemented.** The full
documentation set below was written in Phase 0. Sprint 1 (defined in
[docs/implementation-plan.md](docs/implementation-plan.md)) built a PDF ingestion
pipeline — metadata, text, tables, figures, references, and page-level evidence, for
one PDF at a time, persisted as structured JSON (see "Ingestion Output Layout"
below). Sprint 2 built on that: a local `PaperSource` that reads ingested papers
back, chunking, embedding (`fastembed`), a local vector index (`qdrant-client`
embedded mode), and a retrieval pipeline that returns ranked, cited evidence for a
question, with paper-scoped filtering (see "Retrieval Output Layout" below). See
[docs/decisions.md](docs/decisions.md) ADR-014/ADR-015 for what changed from the
original plan (parser choice, embedding/vector-store choices, small domain-model
additions) and why.

No structured understanding, comparison, landscape, gap analysis, or agent logic
exists yet, and no LLM is used anywhere — retrieval returns the evidence chunk
itself as the "answer," not an LLM-generated one (a deliberate Sprint 2 scoping
decision, see `implementation-plan.md`'s Sprint 2 status note).

Both pipelines have been validated with unit and integration tests (using PDFs
generated on the fly with PyMuPDF, not committed fixtures, and a synthetic retrieval
evaluation set) but **not yet run against a real curated AI/CV/ML paper collection**
— see "Local Development" below for how to try it against your own PDFs.

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
- **Parsing:** PyMuPDF (chosen, Sprint 1 — see ADR-014), Docling (alternative)
- **Embeddings:** `fastembed` / BAAI/bge-small-en-v1.5 (chosen, Sprint 2 — see ADR-015), Jina (alternative); reranking still a future candidate (RET-006)
- **Vector database:** `qdrant-client`, embedded/local mode (chosen, Sprint 2 — see ADR-015), a networked Qdrant server or pgvector (alternatives)
- **Relational/structured storage:** PostgreSQL (still a future candidate — not needed yet)
- **LLM / VLM:** hosted API and/or local model, provider-agnostic via interfaces (not used yet — Sprint 3+)
- **Paper source (future):** arXiv API (candidate; local `PaperSource` chosen for Sprint 2)
- **Frontend (post-MVP):** React + Tailwind
- **Local dev orchestration:** Docker Compose

## Development Roadmap

See [docs/implementation-plan.md](docs/implementation-plan.md) for full detail.

| Sprint | Focus |
|---|---|
| Phase 0 | Planning (this stage) |
| Sprint 1 | Scientific paper ingestion (text/tables/figures/references/metadata) — done |
| Sprint 2 | Paper discovery (curated collection input) and retrieval — done |
| Sprint 3 | Structured paper understanding (problem/method/dataset/metric/result/limitation) — completes the MVP — **current target** |
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
│   │   ├── models/          # Paper, Author, Page, TextBlock, Section, Figure, Table, Citation, Chunk (implemented)
│   │   ├── schemas/         # Shared validation/serialization schemas (not yet needed — see below)
│   │   └── interfaces/      # DocumentParser, EmbeddingProvider, VectorStore, PaperSource (implemented); LLM/VLM (future)
│   ├── ingestion/           # Ingestion orchestration: pipeline, assets, validation, persistence (read+write), report
│   ├── discovery/           # PaperSource capability boundary (interface-only; see infrastructure/paper_sources)
│   ├── retrieval/           # chunking.py, indexing.py (write path), retrieval.py (read path) — implemented
│   ├── infrastructure/
│   │   ├── parsers/          # PyMuPDFDocumentParser + parsing heuristics (implemented)
│   │   ├── embeddings/        # FastEmbedProvider (implemented)
│   │   ├── vector_stores/      # QdrantLocalVectorStore (implemented)
│   │   └── paper_sources/       # LocalCollectionPaperSource (implemented)
│   ├── multimodal/          # Figure/table understanding orchestration (supporting capability, Sprint 8)
│   ├── agent/                # (future) research workflow orchestration
│   ├── tools/                 # (future) agent-invocable capabilities
│   └── api/                   # FastAPI application (future)
│   # understanding/, landscape/, comparison/, gap_analysis/, graph/ are documented
│   # in architecture.md and created when their sprint begins — not scaffolded
│   # ahead of need.
├── tests/
│   ├── unit/                # Domain models, heuristics, pipeline orchestration (fakes only, no real I/O)
│   ├── integration/         # Real parser/embedder/vector-store against generated PDFs
│   └── evaluation/          # Retrieval Recall@K/MRR harness against a synthetic eval set
├── data/
│   ├── papers/
│   │   ├── raw/              # Local input PDFs you place here (gitignored)
│   │   └── processed/         # Ingestion output (gitignored — see "Ingestion Output Layout")
│   ├── index/                  # Local vector index (gitignored — see "Retrieval Output Layout")
│   ├── figures/                # (unused; figures live under papers/processed/<id>/figures/)
│   └── tables/                 # (unused; tables live under papers/processed/<id>/tables/)
├── scripts/
│   ├── ingest.py                # Sprint 1 CLI entry point
│   ├── index.py                  # Sprint 2 CLI: build the local retrieval index
│   └── search.py                  # Sprint 2 CLI: query the index
├── config/                       # Configuration files (not yet needed — no config exists yet)
├── pyproject.toml
├── docker-compose.yml
└── .gitignore
```

`src/domain/schemas` and `config/` remain empty (`.gitkeep` only) — nothing has
needed them yet (see [docs/development-guidelines.md](docs/development-guidelines.md),
"do not over-engineer"). `multimodal/`, `agent/`, `tools/`, and `api/` are scaffolded
but still empty, reserved for their documented future sprints.

## Local Development

Both pipelines are runnable locally. No API keys or `.env` file are needed — nothing
here calls a paid service. `scripts/index.py`/`scripts/search.py` do need network
access on their *first* run only, to download the `fastembed` model (~130MB,
cached afterward under the OS's standard cache directory).

```bash
python -m venv .venv
.venv/Scripts/activate       # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"

# Run the unit test suite (fakes only, no network, no real papers/models needed):
pytest -m "not integration"

# Run everything, including real fastembed/qdrant-client integration tests and the
# evaluation harness (downloads the embedding model on first run):
pytest

# Ingest, then index, then search your own PDFs:
#   1. Place a few open-access PDFs (e.g. from arXiv — respect each paper's license/
#      terms) into data/papers/raw/ (gitignored, nothing there is committed).
python scripts/ingest.py
#      Output: data/papers/processed/<paper_id>/ (gitignored — see "Ingestion Output
#      Layout" below).
python scripts/index.py
#      Output: data/index/ (gitignored — see "Retrieval Output Layout" below).
python scripts/search.py "What dataset was used for evaluation?"
#      Prints ranked evidence chunks with paper + page citations. Add --paper
#      <paper_id> (repeatable) to restrict the search to specific papers.
```

`docker-compose.yml` currently documents planned local services (a networked Qdrant,
PostgreSQL) as comments — Sprint 2 deliberately did not need them (see
[docs/decisions.md](docs/decisions.md) ADR-015, embedded/local `qdrant-client`
instead); it will be filled in only if a real service becomes necessary later.

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

## Retrieval Output Layout

Running `scripts/index.py` writes a local, embedded (no server) `qdrant-client`
store under `data/index/` — see [docs/decisions.md](docs/decisions.md) ADR-015 for
why this is `qdrant-client`'s local mode rather than a networked Qdrant server. It
is not a set of individually meaningful files the way ingestion's output is (it's
Qdrant's own on-disk format), so there's no per-file breakdown here — just know that
each indexed chunk's payload carries `chunk_id`, `paper_id`, `page`, and `text`, which
is exactly what `scripts/search.py` prints back as a citation.

`data/index/` is not committed (same reasoning as `data/papers/processed/` — it's
derived from extracted paper text). If you change the embedding model, delete
`data/index/` and re-run `scripts/index.py`: `QdrantLocalVectorStore` refuses to open
an existing collection built with a different vector dimension rather than silently
producing wrong results.

## Contributing

This is currently a solo portfolio project in the planning stage. See
[docs/development-guidelines.md](docs/development-guidelines.md) for the coding
conventions that will apply once implementation starts.
