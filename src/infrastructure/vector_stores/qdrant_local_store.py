"""VectorStore implementation backed by qdrant-client's embedded/local (on-disk) mode
(ADR-015) — no server process, no Docker.

Confirmed (see this sprint's implementation notes) that local mode implements the
same payload-filtering API as server mode, so RET-002's paper-scoped filtering
requirement is met without any operational service.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.domain.interfaces.vector_store import (
    ScoredChunk,
    Vector,
    VectorRecord,
    VectorStore,
    VectorStoreError,
)

DEFAULT_COLLECTION = "chunks"


class QdrantLocalVectorStore(VectorStore):
    """VectorStore backed by ``QdrantClient(path=...)`` (embedded, on-disk).

    Qdrant point ids must be an unsigned integer or a UUID, not an arbitrary string,
    so each point's id is a deterministic ``uuid5`` derived from its ``chunk_id`` —
    the human-readable ``chunk_id`` itself is kept in the payload and is what
    ``query()`` returns in ``ScoredChunk.chunk_id`` (never the opaque UUID), so
    returned ids stay meaningful outside this store.
    """

    def __init__(
        self,
        storage_path: Path,
        dimension: int,
        collection_name: str = DEFAULT_COLLECTION,
    ) -> None:
        self._client = QdrantClient(path=str(storage_path))
        self._collection = collection_name
        self._ensure_collection(dimension)

    def _ensure_collection(self, dimension: int) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(
                    size=dimension, distance=qmodels.Distance.COSINE
                ),
            )
            return

        info = self._client.get_collection(self._collection)
        existing_size = info.config.params.vectors.size
        if existing_size != dimension:
            raise VectorStoreError(
                f"existing collection '{self._collection}' has dimension "
                f"{existing_size}, but the configured EmbeddingProvider produces "
                f"{dimension}-dim vectors — clear the index directory or use a "
                "matching embedding model."
            )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._client.upsert(
            collection_name=self._collection,
            points=[
                qmodels.PointStruct(
                    id=_point_id(r.chunk_id),
                    vector=r.vector,
                    payload={
                        "chunk_id": r.chunk_id,
                        "paper_id": r.paper_id,
                        "page": r.page,
                        "text": r.text,
                    },
                )
                for r in records
            ],
        )

    def query(
        self, vector: Vector, top_k: int = 5, paper_ids: list[str] | None = None
    ) -> list[ScoredChunk]:
        query_filter = None
        if paper_ids:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="paper_id", match=qmodels.MatchAny(any=paper_ids)
                    )
                ]
            )
        hits = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
            query_filter=query_filter,
        ).points
        return [
            ScoredChunk(
                chunk_id=h.payload["chunk_id"],
                paper_id=h.payload["paper_id"],
                page=h.payload["page"],
                text=h.payload["text"],
                score=h.score,
            )
            for h in hits
        ]

    def delete_paper(self, paper_id: str) -> None:
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="paper_id", match=qmodels.MatchValue(value=paper_id)
                        )
                    ]
                )
            ),
        )

    def close(self) -> None:
        self._client.close()


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))
