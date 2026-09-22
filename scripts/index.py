#!/usr/bin/env python
"""Sprint 2 indexing CLI.

Usage:
    python scripts/index.py                        # index all of data/papers/processed/
    python scripts/index.py --processed-dir some/dir --index-dir some/out

Discovers every paper already ingested (see scripts/ingest.py), chunks it, embeds
the chunks with fastembed, and upserts them into a local (embedded, on-disk)
qdrant-client store — see docs/decisions.md ADR-015 for why these implementations
were chosen. The first run downloads the embedding model (needs network once).
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
from src.infrastructure.paper_sources.local_collection_source import (  # noqa: E402
    LocalCollectionPaperSource,
)
from src.infrastructure.vector_stores.qdrant_local_store import (  # noqa: E402
    QdrantLocalVectorStore,
)
from src.retrieval.indexing import IndexingPipeline  # noqa: E402

DEFAULT_PROCESSED_DIR = REPO_ROOT / "data" / "papers" / "processed"
DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "index"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if not args.quiet else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # fastembed's model download machinery logs at INFO through httpx/huggingface_hub —
    # noisy, not this script's own progress, so keep it to warnings and above.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)

    if not args.processed_dir.is_dir() or not any(
        p.is_dir() for p in args.processed_dir.iterdir()
    ):
        print(
            f"No ingested papers found in {args.processed_dir}. Run "
            "scripts/ingest.py first (see docs/implementation-plan.md Sprint 1)."
        )
        return 1

    try:
        embedder = FastEmbedProvider()
    except EmbeddingError as exc:
        print(f"Could not load the embedding model: {exc}")
        return 2

    args.index_dir.mkdir(parents=True, exist_ok=True)
    store = QdrantLocalVectorStore(storage_path=args.index_dir, dimension=embedder.dimension)
    try:
        source = LocalCollectionPaperSource(processed_root=args.processed_dir)
        pipeline = IndexingPipeline(
            paper_source=source, embedding_provider=embedder, vector_store=store
        )
        report = pipeline.index_all()
    finally:
        # Explicit close rather than relying on QdrantClient.__del__ — on Windows,
        # __del__ running during interpreter shutdown can hit a torn-down msvcrt
        # module and print a spurious traceback even though nothing went wrong.
        store.close()

    print(f"Indexed {report.papers_indexed} papers, {report.chunks_indexed} chunks.")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--quiet", action="store_true", help="Only log warnings/errors.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
