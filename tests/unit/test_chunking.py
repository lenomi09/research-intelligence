"""Unit tests for src/retrieval/chunking.py — pure logic, no I/O."""

from __future__ import annotations

from src.domain.models.paper import Paper
from src.domain.models.text_block import TextBlock
from src.retrieval.chunking import chunk_paper


def _paper(text_blocks: list[TextBlock], paper_id: str = "paper_001") -> Paper:
    return Paper(
        paper_id=paper_id,
        source_path="irrelevant.pdf",
        page_count=max((b.page for b in text_blocks), default=1),
        metadata_source="unavailable",
        text_blocks=text_blocks,
    )


def test_one_chunk_per_short_block() -> None:
    blocks = [
        TextBlock(block_id="block_0001", page=1, text="Intro text.", order=0),
        TextBlock(block_id="block_0002", page=1, text="More text.", order=1),
    ]
    chunks = chunk_paper(_paper(blocks))

    assert len(chunks) == 2
    assert chunks[0].text == "Intro text."
    assert chunks[0].source_block_id == "block_0001"
    assert chunks[0].page == 1
    assert chunks[1].text == "More text."


def test_chunk_ids_are_unique_and_paper_scoped() -> None:
    blocks = [TextBlock(block_id="block_0001", page=1, text="hello", order=0)]
    chunks = chunk_paper(_paper(blocks, paper_id="paper_xyz"))

    assert chunks[0].paper_id == "paper_xyz"
    assert chunks[0].chunk_id.startswith("paper_xyz:block_0001:")


def test_oversized_block_splits_with_overlap() -> None:
    text = "A" * 250
    blocks = [TextBlock(block_id="block_0001", page=3, text=text, order=0)]

    chunks = chunk_paper(_paper(blocks), max_chars=100, overlap_chars=20)

    assert len(chunks) > 1
    assert all(c.page == 3 for c in chunks)
    assert all(c.source_block_id == "block_0001" for c in chunks)
    # Overlap: the tail of one chunk should reappear at the head of the next.
    assert chunks[0].text[-20:] == chunks[1].text[:20]
    # Reassembling without the overlapping tail should reconstruct the original text.
    step = 100 - 20
    reconstructed = "".join(c.text[:step] for c in chunks[:-1]) + chunks[-1].text
    assert reconstructed == text


def test_block_within_budget_is_not_split() -> None:
    text = "short text"
    blocks = [TextBlock(block_id="block_0001", page=1, text=text, order=0)]

    chunks = chunk_paper(_paper(blocks), max_chars=1000, overlap_chars=100)

    assert len(chunks) == 1
    assert chunks[0].text == text


def test_empty_text_blocks_yields_no_chunks() -> None:
    assert chunk_paper(_paper([])) == []


def test_whitespace_only_block_is_dropped() -> None:
    blocks = [TextBlock(block_id="block_0001", page=1, text="   \n  ", order=0)]
    assert chunk_paper(_paper(blocks)) == []


def test_chunks_are_ordered_by_page_then_block_order() -> None:
    blocks = [
        TextBlock(block_id="block_0002", page=2, text="second page", order=0),
        TextBlock(block_id="block_0001", page=1, text="first page, second block", order=1),
        TextBlock(block_id="block_0000", page=1, text="first page, first block", order=0),
    ]
    chunks = chunk_paper(_paper(blocks))

    assert [c.source_block_id for c in chunks] == ["block_0000", "block_0001", "block_0002"]
