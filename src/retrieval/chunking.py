"""Chunking (RET-003): the retrieval-side pipeline stage that turns a Paper's
TextBlocks into Chunks — the unit that gets embedded and indexed.

Deliberately simple (docs/development-guidelines.md, "don't over-engineer"): one
Chunk per TextBlock, unless a block's text exceeds a character budget, in which case
it is split into overlapping character windows. No sentence/token-aware NLP. Every
resulting chunk inherits its parent block's ``page`` and ``block_id`` — this is how
page provenance survives chunking (NFR-011).
"""

from __future__ import annotations

from src.domain.models.chunk import Chunk
from src.domain.models.paper import Paper

DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP_CHARS = 100


def chunk_paper(
    paper: Paper,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    """Chunk one paper's TextBlocks, in page/reading order."""
    chunks: list[Chunk] = []
    order = 0
    for block in sorted(paper.text_blocks, key=lambda b: (b.page, b.order)):
        for piece in _split_text(block.text, max_chars, overlap_chars):
            if not piece.strip():
                continue
            chunks.append(
                Chunk(
                    chunk_id=f"{paper.paper_id}:{block.block_id}:{order}",
                    paper_id=paper.paper_id,
                    page=block.page,
                    text=piece,
                    order=order,
                    source_block_id=block.block_id,
                )
            )
            order += 1
    return chunks


def _split_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split ``text`` into ``max_chars``-sized windows with ``overlap_chars`` of
    overlap between consecutive windows, so a sentence split exactly at a boundary
    isn't lost entirely from either chunk. Returns ``[text]`` unchanged when it
    already fits within ``max_chars``."""
    if len(text) <= max_chars:
        return [text]
    pieces = []
    start = 0
    step = max(max_chars - overlap_chars, 1)
    while start < len(text):
        pieces.append(text[start : start + max_chars])
        start += step
    return pieces
