"""Discovery capability (architecture.md §3): collects/curates the paper collection
via the PaperSource interface (src/domain/interfaces/paper_source.py).

Sprint 2 scope is the manual/local case only — LocalCollectionPaperSource
(src/infrastructure/paper_sources/local_collection_source.py), wired into
scripts/index.py. External search (DISC-003, e.g. arXiv topic search) is explicitly
deferred, per ADR-013 and docs/implementation-plan.md.

There is deliberately no orchestration code in this package beyond the interface
itself: `PaperSource.list_papers()` already is the whole capability at this sprint's
scope, and `IndexingPipeline` (src/retrieval/indexing.py) is what calls it — a
wrapper here that only forwards to `PaperSource` would be needless indirection (see
docs/development-guidelines.md, "avoiding unnecessary abstraction").
"""
