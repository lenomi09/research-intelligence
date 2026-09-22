#!/usr/bin/env python
"""Sprint 3 understanding CLI.

Usage:
    python scripts/understand.py
    python scripts/understand.py --processed-dir some/dir --index-dir some/out

Reads every already-ingested, already-indexed paper (see scripts/ingest.py and
scripts/index.py), extracts research problem/methodology/dataset/metric/result/
limitation with evidence pointers (FR-030–FR-035) via an LLM, and persists an
understanding.json per paper. Requires LLM_BASE_URL and LLM_MODEL (and usually
LLM_API_KEY) environment variables pointing at an OpenAI-compatible endpoint — see
README.md "Running Sprint 3" for how to point this at a local Ollama instance.
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
from src.domain.interfaces.llm_provider import LLMError  # noqa: E402
from src.infrastructure.embeddings.fastembed_provider import FastEmbedProvider  # noqa: E402
from src.infrastructure.llm.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleLLMProvider,
)
from src.infrastructure.paper_sources.local_collection_source import (  # noqa: E402
    LocalCollectionPaperSource,
)
from src.infrastructure.vector_stores.qdrant_local_store import (  # noqa: E402
    QdrantLocalVectorStore,
)
from src.retrieval.retrieval import RetrievalPipeline  # noqa: E402
from src.understanding.pipeline import UnderstandingPipeline  # noqa: E402

DEFAULT_PROCESSED_DIR = REPO_ROOT / "data" / "papers" / "processed"
DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "index"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if not args.quiet else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
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

    try:
        llm = OpenAICompatibleLLMProvider()
    except LLMError as exc:
        print(f"Could not construct the LLM provider: {exc}")
        return 2

    store = QdrantLocalVectorStore(storage_path=args.index_dir, dimension=embedder.dimension)
    try:
        source = LocalCollectionPaperSource(processed_root=args.processed_dir)
        retrieval = RetrievalPipeline(embedding_provider=embedder, vector_store=store)
        pipeline = UnderstandingPipeline(
            paper_source=source,
            retrieval_pipeline=retrieval,
            llm_provider=llm,
            output_root=args.processed_dir,
        )
        report = pipeline.understand_all()
    finally:
        # See scripts/index.py for why this is an explicit close rather than
        # relying on QdrantClient.__del__.
        store.close()

    print(
        f"Processed {report.papers_processed} papers: "
        f"{report.papers_understood} understood, {report.papers_failed} failed."
    )
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--quiet", action="store_true", help="Only log warnings/errors.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
