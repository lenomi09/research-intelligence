# Development Guidelines

**Status:** Phase 0 — Planning
**Last updated:** 2026-09-22

These are engineering rules for this project. They exist to keep the codebase
maintainable for a solo developer over a multi-phase build, and to support the
architectural goals in `architecture.md` (provider independence, testability).

## Guiding Principle: Do Not Over-Engineer the MVP

Only introduce an abstraction (interface, base class, plugin system) for something that
is likely to change or that needs to be mocked for testing. The six domain interfaces in
`architecture.md` (`LLMProvider`, `VLMProvider`, `EmbeddingProvider`, `VectorStore`,
`DocumentParser`, `PaperSource`) meet that bar — they wrap external vendors/services/data
sources that we explicitly want to swap and mock. Internal application logic (e.g. a
single chunking function, a single comparison-formatting step) does **not** need an
interface unless a second implementation is actually planned. When in doubt, write the
concrete version first; extract an interface when a second real use case appears.

This also applies to capability modules themselves: do not create
`src/discovery`, `src/understanding`, `src/landscape`, `src/comparison`,
`src/gap_analysis`, or `src/graph` (see `architecture.md` §3) until the sprint that
needs them arrives, even though the target architecture documents all of them now.
Scaffolding a directory for a capability nobody has implemented yet is exactly the kind
of speculative structure this principle warns against.

## Guiding Principle: Prefer Deterministic Pipelines Over Agents

Default to fixed, deterministic sequences of steps for every capability (see ADR-006 and
ADR-012 in `decisions.md`). Do not reach for an agent framework or dynamic tool-selection
logic just because the project is AI-related — introduce agentic orchestration only once
a capability genuinely needs runtime-variable multi-step reasoning that a fixed pipeline
cannot express, and only after that capability's building blocks already work
deterministically. `src/agent` and `src/tools` stay empty until that need is concrete.

## Python Conventions

- Target a recent stable Python 3 version (pin exact version in `pyproject.toml` once
  chosen).
- Follow PEP 8; `ruff` is configured (`pyproject.toml` `[tool.ruff]`) for linting
  (`ruff check .`) and formatting (`ruff format .`) — run both before considering a
  change done. The configured ruleset is deliberately small (pyflakes, import
  sorting, bugbear, pyupgrade); it is not a strict/opinionated style enforcer, and
  should stay that way rather than accumulating rules nobody asked for.
- Prefer explicit, readable code over clever one-liners.
- Keep functions small and single-purpose; a function that does I/O and business logic
  in one body is a sign to split it.

## Type Hints

- All new functions and public methods should have type hints on parameters and return
  values.
- Domain models and schemas (`src/domain/models`, `src/domain/schemas`) must be fully
  typed — they are the contract between layers.
- Avoid `Any` except at genuine boundaries (e.g. parsing a third-party library's loosely
  typed response) — and narrow it immediately.

## Error Handling

- Don't swallow exceptions silently. A caught exception must be logged with context or
  re-raised (possibly wrapped in a domain-specific exception).
- Distinguish expected failure modes (e.g. "this page failed to parse") from programmer
  errors — the former should be handled and logged per NFR-006; the latter should
  propagate.
- Define a small set of domain-level exceptions (e.g. `ParsingError`, `RetrievalError`)
  rather than leaking library-specific exception types across layer boundaries.

## Logging

- Use structured logging (e.g. Python's `logging` module with consistent fields: stage,
  paper/document id, page, error) so ingestion/retrieval/generation issues are
  debuggable after the fact (NFR-004).
- Log at pipeline boundaries: ingestion start/end per paper, retrieval query + result
  count, generation call + evidence used.
- Do not log secrets (API keys) or full raw model prompts/responses at default log level
  if they may contain sensitive content — use debug level for verbose payloads.

## Configuration

- All environment-dependent values (API keys, provider selection, storage paths, model
  names) come from configuration, not hard-coded literals (NFR-008).
- Centralize configuration loading (e.g. a single `config` module/`Settings` object) so
  there is one place that reads environment variables.
- Provider selection (which `LLMProvider`/`VLMProvider`/etc. implementation to use) is a
  config value, resolved through a factory — application code never imports a specific
  vendor implementation directly (supports NFR-009).

## Environment Variables

- All secrets and environment-specific values are supplied via environment variables,
  loaded from a local `.env` file in development (never committed — see `.gitignore`).
- Provide an `.env.example` (added when the first real config values are known, i.e.
  Phase 1+) documenting required variables without real values.
- Never commit a populated `.env` file.

## Testing Strategy

- **Unit tests** (`tests/unit`): domain models, pure logic, application logic tested
  against fake/mock implementations of domain interfaces — no network calls, no real
  parser/LLM/vector store.
- **Integration tests** (`tests/integration`): real implementations (e.g. actual parser
  against a real PDF) — slower, run less frequently, may require local services (e.g. a
  local Qdrant instance via Docker Compose).
- **Evaluation tests** (`tests/evaluation`): correctness/quality checks against curated
  or benchmark datasets, per `evaluation.md` — distinct from pass/fail unit tests; these
  produce metrics, not just green/red.
- Every domain interface should have at least one fake/mock implementation usable in unit
  tests, in addition to its real infrastructure implementation.

## Dependency Management

- Use `pyproject.toml` as the single source of truth for dependencies.
- Add a dependency only when it's needed for the current phase's work — do not
  pre-install libraries for future phases (per the task constraints for Phase 0).
- Prefer well-maintained, widely used libraries; document why a less common library was
  chosen if applicable (e.g. in `decisions.md`).

## Git Conventions

- `main`/`master` stays deployable/demo-able at each phase boundary; use feature
  branches for in-progress work if working with branches.
- Commit messages: concise, imperative mood, explain *why* when not obvious from the
  diff. Conventional Commits style (`feat:`, `fix:`, `docs:`, `chore:`, `test:`) is
  recommended for a clean history but not strictly enforced for a solo project.
- Keep commits scoped to one logical change; avoid mixing unrelated refactors with
  feature work.

## Module Boundaries

- `src/domain` has no dependency on any other `src/*` package or third-party
  infrastructure library (no LLM SDKs, no HTTP clients, no DB drivers).
- `src/infrastructure` may depend on `src/domain` (to implement its interfaces) and on
  third-party libraries; it must not be imported by `src/domain`.
- Capability modules (`src/discovery`, `src/ingestion`, `src/understanding`,
  `src/retrieval`, `src/landscape`, `src/comparison`, `src/gap_analysis`, `src/graph`,
  `src/multimodal`, and eventually `src/agent`/`src/tools`) depend on `src/domain`
  interfaces/models, and are wired to concrete `src/infrastructure` implementations only
  at composition/startup time (e.g. in the API app factory or a dedicated wiring
  module), not via direct imports scattered through the code. A capability module may
  depend on another capability module's public interface (e.g. `comparison` depends on
  `understanding`'s output types) but never reaches into its internals.
- `src/api` depends on the application layer and domain schemas; it must not import
  `src/infrastructure` directly.

## Interface Design

- Keep interfaces narrow — define only the methods actually called by application code
  today, not a speculative full API surface of the underlying vendor.
- Interfaces live in `src/domain/interfaces` and use only domain types (or primitives) in
  their signatures — never a vendor SDK type.
- Prefer explicit method names describing intent (e.g. `embed_texts`, `similarity_search`)
  over generic ones (e.g. `run`, `call`).

## Provider Abstraction

- Every provider-backed capability (parsing, embedding, reranking, vector search, LLM
  generation, VLM generation) is accessed only through its domain interface from
  application code.
- New provider implementations go in `src/infrastructure/<capability>/<provider>.py` (or
  similar), implementing the corresponding interface.
- Provider selection happens via configuration (see Configuration above), resolved once
  at startup, not scattered `if provider == "x"` checks through business logic.

## Avoiding Hard-Coded Credentials

- No API keys, tokens, passwords, or connection strings in source code, ever — including
  in tests, scripts, or comments.
- `.env`, `.env.*` (except `.env.example`), and any local secrets files are in
  `.gitignore` from the start.
- If a secret is accidentally committed, treat it as compromised: rotate it, don't just
  remove it from a future commit.

## Avoiding Unnecessary Abstraction

- Do not create a plugin system, registry, or factory for something with only one
  implementation and no near-term plan for a second.
- Do not add configuration flags for behavior nobody has asked for yet.
- Do not build landscape, comparison, gap-analysis, graph, multimodal, or agentic
  features early "while we're in there" — sequence follows `implementation-plan.md`'s
  sprint order, even when a later capability seems like an easy extension of the one
  currently being built.
- Prefer deleting speculative code over maintaining it if a planned second use case does
  not materialize.
