"""Retrieval orchestration (architecture.md §4.2): embeds a question and returns
ranked evidence chunks with citations. No LLM/generation step here — Sprint 2
interprets RET-007 ("grounded answer generation with citations") narrowly: the
chunk text itself is the answer, with its citation attached. Sprint 3 (Understanding)
reuses this pipeline as its evidence source; EvidenceChunk carries chunk_id
specifically so Understanding can cite evidence at chunk granularity, not just page
(ADR-009, ADR-016) — two fields' evidence can share a page but not a chunk.
"""

from __future__ import annotations

from typing import NamedTuple

from src.domain.interfaces.embedding_provider import EmbeddingProvider
from src.domain.interfaces.vector_store import VectorStore

DEFAULT_TOP_K = 5


class EvidenceChunk(NamedTuple):
    """One retrieved piece of grounded evidence: the chunk text plus its citation
    (paper_id, page, chunk_id) and similarity score."""

    paper_id: str
    page: int
    chunk_id: str
    text: str
    score: float


class RetrievalPipeline:
    """Embeds a question and returns ranked evidence chunks with citations."""

    def __init__(
        self, embedding_provider: EmbeddingProvider, vector_store: VectorStore
    ) -> None:
        self._embed = embedding_provider
        self._store = vector_store

    def retrieve(
        self,
        question: str,
        top_k: int = DEFAULT_TOP_K,
        paper_ids: list[str] | None = None,
    ) -> list[EvidenceChunk]:
        vector = self._embed.embed_query(question)
        hits = self._store.query(vector, top_k=top_k, paper_ids=paper_ids)
        return [
            EvidenceChunk(
                paper_id=h.paper_id,
                page=h.page,
                chunk_id=h.chunk_id,
                text=h.text,
                score=h.score,
            )
            for h in hits
        ]
