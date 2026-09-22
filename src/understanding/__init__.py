"""Understanding capability (architecture.md §3, §4.3): turns an ingested, indexed
paper into structured research knowledge — research problem, methodology, dataset,
metric, result, limitation — each with an evidence pointer (FR-030–FR-035, ADR-009).

A fixed, deterministic pipeline (ADR-006/ADR-012): per-field evidence retrieval
(reusing src/retrieval's RetrievalPipeline) feeds one LLMProvider call per paper;
the LLM only ever selects among already-retrieved, code-labeled evidence chunks
(never free-generates a page number) — see prompting.py and ADR-016.
"""
