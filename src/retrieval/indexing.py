"""Indexing orchestration (architecture.md §3 "Retrieval"): discovers papers via
PaperSource, chunks them, embeds the chunks, and upserts them into the VectorStore —
the retrieval-side analog of IngestionPipeline. Depends only on domain interfaces;
concrete implementations are injected by the caller (see scripts/index.py), per
NFR-009 provider replaceability.
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from src.domain.interfaces.embedding_provider import EmbeddingProvider
from src.domain.interfaces.paper_source import PaperSource
from src.domain.interfaces.vector_store import VectorRecord, VectorStore
from src.retrieval.chunking import chunk_paper

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 32


class IndexingReport(NamedTuple):
    papers_indexed: int
    chunks_indexed: int


class IndexingPipeline:
    """Indexes every paper a PaperSource provides into a VectorStore."""

    def __init__(
        self,
        paper_source: PaperSource,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._source = paper_source
        self._embed = embedding_provider
        self._store = vector_store
        self._batch_size = batch_size

    def index_all(self) -> IndexingReport:
        papers = self._source.list_papers()
        total_chunks = 0

        for paper in papers:
            chunks = chunk_paper(paper)
            # Idempotent re-indexing: clear this paper's old chunks before
            # upserting new ones, so re-running doesn't accumulate stale points.
            self._store.delete_paper(paper.paper_id)

            for start in range(0, len(chunks), self._batch_size):
                batch = chunks[start : start + self._batch_size]
                vectors = self._embed.embed_documents([c.text for c in batch])
                records = [
                    VectorRecord(
                        chunk_id=c.chunk_id,
                        vector=v,
                        paper_id=c.paper_id,
                        page=c.page,
                        text=c.text,
                    )
                    for c, v in zip(batch, vectors, strict=True)
                ]
                self._store.upsert(records)

            total_chunks += len(chunks)
            logger.info(
                "stage=indexing paper_id=%s status=done chunks=%s",
                paper.paper_id,
                len(chunks),
            )

        return IndexingReport(papers_indexed=len(papers), chunks_indexed=total_chunks)
