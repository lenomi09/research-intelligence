#!/usr/bin/env python
"""Sprint 2 search CLI.

Usage:
    python scripts/search.py "What dataset was used for evaluation?"
    python scripts/search.py "..." --top-k 3 --paper paper_001 --paper paper_002

Embeds the question, queries the local vector index built by scripts/index.py, and
prints ranked evidence chunks with their citations (paper + page). No LLM is
involved — the retrieved chunk text itself is the answer (see docs/decisions.md
ADR-015 and docs/implementation-plan.md Sprint 2's narrow RET-007 interpretation).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.domain.interfaces.embedding_provider import EmbeddingError  # noqa: E402
from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider  # noqa: E402
from src.infrastructure.vector_stores.qdrant_local_store import (  # noqa: E402
    QdrantLocalVectorStore,
)
from src.retrieval.retrieval import RetrievalPipeline  # noqa: E402

DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "index"
DEFAULT_TOP_K = 5


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    # fastembed's model download machinery logs at INFO through httpx/huggingface_hub —
    # noisy, not this script's own output, so keep it to warnings and above.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

    if not args.index_dir.is_dir():
        print(
            f"No index found at {args.index_dir}. Run scripts/index.py first "
            "(see docs/implementation-plan.md Sprint 2)."
        )
        return 1

    try:
        embedder = FastEmbedProvider()
    except EmbeddingError as exc:
        print(f"Could not load the embedding model: {exc}")
        return 2

    store = QdrantLocalVectorStore(storage_path=args.index_dir, dimension=embedder.dimension)
    pipeline = RetrievalPipeline(embedding_provider=embedder, vector_store=store)
    results = pipeline.retrieve(args.question, top_k=args.top_k, paper_ids=args.paper or None)

    if not results:
        print(
            "No evidence found. Has scripts/index.py been run against a non-empty collection?"
        )
        return 0

    for i, result in enumerate(results, start=1):
        print(f"[{i}] {result.paper_id} p.{result.page} (score={result.score:.3f})")
        print(f"    {result.text}\n")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="Natural-language question to search for.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--paper", action="append", help="Restrict to this paper_id (repeatable)."
    )
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
