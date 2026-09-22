# CLAUDE.md

Instructions for Claude Code sessions working in this repository. This file tells
you the rules and where to look — it does not duplicate the documents it points to.
If this file and `docs/` ever disagree, `docs/` (especially `decisions.md`) wins;
flag the discrepancy rather than silently picking one.

## 1. Project Overview

**Research Intelligence Platform** — transforms a *collection* of scientific papers
into structured, evidence-backed research intelligence (per-paper structured
knowledge, multi-paper comparison, research landscape, gap hypotheses), not a
single-document "chat with PDF" tool. Full product context: `docs/PRD.md`.

**Current state:** Sprints 1–3 are implemented. Sprint 1 (Scientific Paper
Ingestion): PDF → text blocks, sections, figures, tables, citations, page metadata →
persisted JSON (`scripts/ingest.py`). Sprint 2 (Discovery and Retrieval): reads that
persisted output back (`src/discovery`, `LocalCollectionPaperSource`), chunks and
embeds it (`fastembed`), indexes it in a local vector store (`qdrant-client`
embedded mode), and answers a question with ranked, cited evidence chunks —
no LLM involved (`scripts/index.py`, `scripts/search.py`; see ADR-015). Sprint 3
(Structured Paper Understanding): for each paper, retrieves and labels evidence per
FR-030–035 field (`src/understanding/prompting.py`'s `collect_labeled_evidence`),
makes one `LLMProvider.complete()` call to extract research problem/methodology/
dataset/metric/result/limitation, resolves cited evidence labels back to real
chunks (never trusts a page number the LLM reports itself), and persists
`understanding.json` per paper (`scripts/understand.py`; see ADR-016). This is the
first sprint using an LLM — `OpenAICompatibleLLMProvider` (`httpx`-based,
provider-neutral) is the only implementation; **no LLM API key or local Ollama
instance was available in this environment**, so Sprint 3 is validated with mocked
HTTP and a fake deterministic `LLMProvider`, not a real endpoint (a real-endpoint
smoke test exists at `pytest -m llm`, skipped by default). Nothing past
Understanding exists yet — see `docs/implementation-plan.md` for the roadmap and
`docs/product-backlog.md` for itemized scope.

## 2. Architectural Principles (non-negotiable)

- **Multi-paper is the product; single-document Q&A is a supporting capability**
  (ADR-007). Don't reframe work around single-PDF chat.
- **Layered dependencies, pointing inward:** API → application capabilities →
  domain interfaces → infrastructure implementations. Domain never imports
  infrastructure or third-party libraries. See `docs/architecture.md` §2.
- **Provider/source independence:** every external dependency (parser, LLM, VLM,
  embeddings, vector store, paper source) sits behind a `src/domain/interfaces`
  interface. Application code never imports a vendor SDK or concrete parser
  directly outside `src/infrastructure` and composition roots (`scripts/*.py`).
- **Deterministic pipelines before agents** (ADR-006, ADR-012). Don't introduce
  agent/orchestration machinery because "this is an AI project" — only when a
  capability genuinely needs runtime tool selection, after its building blocks
  already work deterministically.
- **Evidence traceability is a hard requirement** (ADR-009, NFR-011): anything
  presented as a claim/citation must carry a pointer to its source page (and
  figure/table where applicable). Never fabricate metadata, captions, or page
  numbers when they weren't actually found — leave the field `None`/empty instead.
- **Gap/landscape output is a hypothesis, never a fact** (ADR-010) — relevant once
  Sprint 6+ exists; keep in mind when touching anything that surfaces a pattern.

## 3. Authoritative Documentation

| Question | Where to look |
|---|---|
| Product goals, scope, non-goals | `docs/PRD.md` |
| Functional/non-functional requirements (FR-/NFR- IDs) | `docs/requirements.md` |
| System design, layering, domain model, diagrams | `docs/architecture.md` |
| Roadmap, sprint scope, Definition of Done | `docs/implementation-plan.md` |
| Backlog items, priorities, acceptance criteria | `docs/product-backlog.md` |
| Metrics, what's planned vs. implemented vs. measured | `docs/evaluation.md` |
| Why a decision was made, alternatives considered | `docs/decisions.md` (ADR log) |
| Coding rules, module boundaries, testing strategy | `docs/development-guidelines.md` |

Read the relevant doc before making a non-trivial change. Don't infer architecture
from code alone when a doc exists.

## 4. Technology Stack

Runtime deps are added **only when a sprint needs them** — see `pyproject.toml` for
what's actually installed (currently: `pymupdf`, `pydantic`, `fastembed`,
`qdrant-client`, `httpx`; dev: `pytest`, `ruff`). An LLM is now in use (Sprint 3),
but only behind `LLMProvider` via `httpx` — no vendor LLM SDK (`openai`,
`anthropic`) is a dependency, and none should become one without a new ADR. Do not
add VLM libraries until the sprint that needs them (Sprint 8+, see
`docs/implementation-plan.md`). No LLM API key or local Ollama instance was
available when Sprint 3 was built in this environment — don't assume one exists
without checking; see `README.md`'s "Running Sprint 3" for how a user provides one.
Candidate technologies not yet chosen are listed in `docs/architecture.md` §8 —
"candidate" means not yet chosen, not "assumed"; ADR-014/ADR-015/ADR-016 record what
was actually picked and why.

## 5. Source Organization

```
src/domain/{models,schemas,interfaces}   # no third-party or infra imports, ever
src/infrastructure/<capability>/         # concrete provider implementations
src/ingestion/, src/retrieval/, ...      # capability modules (application layer)
src/api/                                 # future — not implemented yet
scripts/                                 # composition roots (CLI entry points) —
                                          # the only place allowed to wire a concrete
                                          # infrastructure implementation into a
                                          # capability module
```

`discovery/`, `retrieval/`, and `understanding/` exist (Sprints 2–3). Capability
directories for later sprints (`landscape/`, `comparison/`, `gap_analysis/`,
`graph/`) are documented in `docs/architecture.md` §3 but **do not exist yet** —
create one only when its sprint starts, not ahead of need.

## 6. Domain / Infrastructure Boundary

- `src/domain/interfaces` defines the contract (e.g. `DocumentParser`); only domain
  types/primitives in signatures, never a vendor SDK type.
- `src/infrastructure/<capability>` implements the interface against a real library.
- Capability modules (`src/ingestion`, etc.) depend on the **interface**, never on a
  concrete `src/infrastructure` class. Wiring a concrete implementation into a
  capability module happens only in a composition root (a `scripts/*.py` entry
  point) — see `src/ingestion/pipeline.py` + `scripts/ingest.py` for the pattern.
- A capability module may depend on another capability module's public output types,
  never its internals.

## 7. Coding Conventions

- Python 3.11+, full type hints on all new functions/methods, `from __future__ import
  annotations` at the top of new modules.
- `pathlib.Path`, not string paths.
- Domain models are Pydantic `BaseModel`s — data + light validation only, no behavior
  beyond that.
- Prefer returning new values over mutating caller-supplied collections passed as
  arguments (avoid "output parameters").
- No comments that restate what the code does; comments explain *why* (a non-obvious
  constraint, a documented limitation, a reference to an FR/NFR/ADR).
- Full rules: `docs/development-guidelines.md`.

## 8. Type Safety

Every function signature is fully typed, including private helpers. Avoid `Any`
except at a genuine third-party boundary (e.g. a loosely-typed PyMuPDF dict), and
narrow it immediately. `ruff` is configured (lint + format, see §7/§17) but there is
**no static type checker** (mypy/pyright) in this repo yet — don't assume one runs in
CI; check `pyproject.toml` before claiming otherwise.

## 9. Error Handling

- Distinguish **required** failures (the document can't be ingested at all — raise
  `ParsingError`/`InvalidDocumentError`) from **optional** failures (one figure/table/
  caption couldn't be extracted — log + append to a warnings list, keep going). See
  `src/domain/interfaces/document_parser.py` and `src/infrastructure/parsers/
  pymupdf_parser.py` for the pattern.
- Never silently swallow an exception or fabricate a value to paper over a failure
  (NFR-006). A missing field is `None`/empty + a warning, not a guess.
- Catch specific exceptions where the failure mode is known; a broad `except
  Exception` is acceptable only around a genuinely optional, per-item extraction
  step, and must log + record a warning, not just `pass`.

## 10. Logging

- Standard library `logging`, module-level `logger = logging.getLogger(__name__)`.
- Structured-ish key=value messages (`"stage=%s paper_id=%s page=%s error=%s"`), not
  free text, so failures are greppable.
- Never log secrets or full raw model prompts/responses at INFO level.

## 11. Configuration / Secrets

- No dependency needing an API key exists yet. When one is added: all secrets via
  environment variables, never hard-coded, never committed. `.env`/`.env.*` (except
  `.env.example`) are already gitignored — keep it that way.
- No config module exists yet (`src/domain/schemas`, `config/` are still empty) —
  don't build one speculatively; add it when a sprint actually needs configurable
  provider selection.

## 12. Testing

- `tests/unit/`: pure logic and fake-collaborator tests (see `tests/unit/
  test_pipeline.py`'s `_FakeParser` pattern) — no real I/O, no real PDFs.
- `tests/integration/`: real implementations against real (or synthetically
  generated, via PyMuPDF itself — see `tests/integration/conftest.py`) PDFs. Never
  commit binary PDF fixtures; generate them in a fixture instead.
- `tests/evaluation/`: a real Recall@K/MRR harness exists (Sprint 2, RET-008)
  against a small synthetic corpus — clearly labeled as such, not a validated
  measurement against real papers. Formal benchmark-dataset infrastructure is still
  Sprint 6+.
- Run with `pytest` (repo root; `pyproject.toml` sets `pythonpath = ["."]`).
- Every new capability needs both a unit test path (fake collaborators) and, where
  it touches a real library, an integration test.
- Don't weaken or delete a test to make a change pass — fix the code, or justify in
  writing why the test's expectation was wrong.

## 13. Dependency Management

- `pyproject.toml` is the single source of truth. Add a dependency only when the
  current sprint's work needs it — never speculatively for a future sprint.
- Prefer the smallest reasonable dependency (see ADR-014 for the PyMuPDF-over-Docling
  reasoning as a worked example of this tradeoff).

## 14. Git Safety

- Never `git push`, force-push, rewrite history, or `git reset --hard` unless
  explicitly asked.
- Never commit secrets, `.env` files, or files under `data/papers/raw|processed`
  (raw papers may be copyrighted; processed output contains extracted paper text —
  both are gitignored on purpose, keep it that way).
- Inspect `git status`/`git diff` before staging; stage specific paths, not blanket
  `git add -A`, when anything unexpected shows up.
- Only commit when asked to.

## 15. Documentation / ADR Rules

- A genuine architectural decision (a real tradeoff with alternatives, not an
  implementation detail) gets an ADR appended to `docs/decisions.md` — never edit or
  renumber a previous ADR's identity; add a new one and mark the old one revised/
  superseded if needed.
- Don't write an ADR for a bug fix or an internal refactor with no alternatives
  worth recording.
- If you change what a doc describes as planned/future into implemented, update that
  doc's status inline (see how `docs/implementation-plan.md` marks Sprint 1 done) —
  don't leave docs claiming something is unimplemented once it isn't, or vice versa.

## 16. Approaching a New Feature

1. Find the feature in `docs/product-backlog.md` / `docs/implementation-plan.md`. If
   it isn't there, stop and ask whether it's actually in scope for the current
   sprint — don't implement ahead of the roadmap.
2. Read the relevant `docs/architecture.md` section for how it's supposed to fit.
3. Check `docs/decisions.md` for any ADR that already constrains the approach.
4. Implement the smallest version that satisfies the backlog item's acceptance
   criteria — no speculative abstraction for hypothetical future needs.
5. Add unit tests (fakes) and, if it touches a real library, integration tests.
6. Update the specific docs that are now inaccurate (see §15) — not the whole set.

## 17. Before Declaring a Task Complete

- Run `ruff check .` and `ruff format --check .`, and the full test suite (`pytest`);
  report the actual results — don't claim any of them pass without running them.
- Re-read your own diff (`git diff`) looking for: leftover debug code, unused
  imports, functions that grew too many parameters, duplicated logic, silently
  swallowed exceptions, hard-coded paths/values that should be parameters.
- Confirm you didn't implement anything from a later sprint "while you were in
  there" (see `docs/development-guidelines.md` "Avoiding Unnecessary Abstraction").
- Confirm docs affected by the change are still accurate.
- State known limitations honestly rather than implying the work is more complete/
  accurate than it is (this project's own NFR-006 applies to your own reporting too).

## 18. Against Over-Engineering

- Don't introduce an interface, factory, registry, or plugin system for something
  with exactly one implementation and no concrete second one planned.
- Don't create a capability directory (`discovery/`, `understanding/`, etc.) before
  its sprint starts, even though the target architecture names it.
- Don't split a working function into many tiny ones without a concrete
  readability/testability win — a long function with clear, linear steps is often
  better than ten one-line indirections.
- Don't add config flags, environment variables, or abstraction layers for behavior
  nobody has asked for yet. When in doubt, write the concrete version first and
  extract an interface only when a second real use case appears.
