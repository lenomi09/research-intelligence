"""Retrieval orchestration (architecture.md §4.2): embeds a question and returns
ranked evidence chunks with citations. No LLM/generation step — Sprint 2 interprets
RET-007 ("grounded answer generation with citations") narrowly: the chunk text
itself is the answer, with its citation attached. Generation/paraphrasing is a
Sprint 3 (Understanding, LLMProvider) concern.
"""

from __future__ import annotations

from typing import NamedTuple

from src.domain.interfaces.embedding_provider import EmbeddingProvider
from src.domain.interfaces.vector_store import VectorStore

DEFAULT_TOP_K = 5


class EvidenceChunk(NamedTuple):
    """One retrieved piece of grounded evidence: the chunk text plus its citation
    (paper_id, page) and similarity score."""

    paper_id: str
    page: int
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
            EvidenceChunk(paper_id=h.paper_id, page=h.page, text=h.text, score=h.score)
            for h in hits
        ]
