"""Integration tests: real QdrantLocalVectorStore (real qdrant-client, embedded/
local on-disk mode, no server)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.interfaces.vector_store import VectorRecord, VectorStoreError
from src.infrastructure.vector_stores.qdrant_local_store import QdrantLocalVectorStore

pytestmark = pytest.mark.integration

DIM = 4


def _records() -> list[VectorRecord]:
    return [
        VectorRecord(
            chunk_id="paper_a:block_0001:0",
            vector=[1, 0, 0, 0],
            paper_id="paper_a",
            page=1,
            text="alpha content",
        ),
        VectorRecord(
            chunk_id="paper_b:block_0001:0",
            vector=[0, 1, 0, 0],
            paper_id="paper_b",
            page=2,
            text="beta content",
        ),
    ]


def test_upsert_and_unfiltered_query_returns_both_papers(tmp_path: Path) -> None:
    store = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store.upsert(_records())

    hits = store.query([1, 0, 0, 0], top_k=5)

    assert {h.paper_id for h in hits} == {"paper_a", "paper_b"}
    store.close()


def test_paper_scoped_filter_returns_only_that_paper(tmp_path: Path) -> None:
    store = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store.upsert(_records())

    hits = store.query([1, 0, 0, 0], top_k=5, paper_ids=["paper_b"])

    assert len(hits) == 1
    assert hits[0].paper_id == "paper_b"
    assert hits[0].chunk_id == "paper_b:block_0001:0"
    store.close()


def test_delete_paper_removes_only_that_papers_points(tmp_path: Path) -> None:
    store = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store.upsert(_records())

    store.delete_paper("paper_a")
    hits = store.query([1, 0, 0, 0], top_k=5)

    assert {h.paper_id for h in hits} == {"paper_b"}
    store.close()


def test_reopening_store_at_same_path_round_trips_data(tmp_path: Path) -> None:
    store1 = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store1.upsert(_records())
    store1.close()

    store2 = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    hits = store2.query([0, 1, 0, 0], top_k=5)

    assert any(h.paper_id == "paper_b" for h in hits)
    store2.close()


def test_dimension_mismatch_on_existing_collection_raises(tmp_path: Path) -> None:
    store1 = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store1.upsert(_records())
    store1.close()

    with pytest.raises(VectorStoreError):
        QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM + 1)


def test_upsert_empty_list_is_a_no_op(tmp_path: Path) -> None:
    store = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store.upsert([])
    assert store.query([1, 0, 0, 0], top_k=5) == []
    store.close()


def test_empty_paper_ids_list_restricts_to_zero_papers_not_unfiltered(
    tmp_path: Path,
) -> None:
    """Regression test: an explicit empty paper_ids list must not silently fall
    back to an unfiltered search — it should restrict to nothing, distinct from
    paper_ids=None (no restriction)."""
    store = QdrantLocalVectorStore(storage_path=tmp_path, dimension=DIM)
    store.upsert(_records())

    assert store.query([1, 0, 0, 0], top_k=5, paper_ids=[]) == []
    assert len(store.query([1, 0, 0, 0], top_k=5, paper_ids=None)) == 2
    store.close()
