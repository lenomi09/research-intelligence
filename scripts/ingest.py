#!/usr/bin/env python
"""Sprint 1 ingestion CLI.

Usage:
    python scripts/ingest.py                          # ingest data/papers/raw/*.pdf
    python scripts/ingest.py path/to/one.pdf another.pdf
    python scripts/ingest.py --input-dir some/dir --output-dir some/out

Ingests one or more PDFs with PyMuPDFDocumentParser, writes structured output under
the output directory (default: data/papers/processed/), and prints a validation
summary per paper plus a corpus-level summary — see docs/implementation-plan.md
Sprint 1 "Definition of Done" for what this is meant to demonstrate.

To try this against real papers: place a handful of open-access PDFs (e.g. from
arXiv — respect each paper's license/terms) in data/papers/raw/, then run this
script with no arguments. Neither data/papers/raw/ nor data/papers/processed/ are
committed to version control (see .gitignore) — the pipeline itself is fully
unit-testable without any real papers present (see tests/).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.infrastructure.parsers.pymupdf_parser import PyMuPDFDocumentParser  # noqa: E402
from src.ingestion.pipeline import IngestionPipeline  # noqa: E402
from src.ingestion.report import IngestionReport  # noqa: E402

DEFAULT_INPUT_DIR = REPO_ROOT / "data" / "papers" / "raw"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "papers" / "processed"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if not args.quiet else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    pdf_paths = _resolve_pdf_paths(args)
    if not pdf_paths:
        print(
            f"No PDFs found. Place PDFs in {args.input_dir} or pass paths explicitly.\n"
            "See docs/implementation-plan.md Sprint 1 scope for where to source a "
            "small open-access AI/CV/ML test corpus (e.g. arXiv)."
        )
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    parser = PyMuPDFDocumentParser()
    pipeline = IngestionPipeline(parser=parser, output_root=args.output_dir)

    reports: list[IngestionReport] = []
    for pdf_path in pdf_paths:
        report = pipeline.ingest(pdf_path)
        reports.append(report)
        _print_report(report)

    _print_corpus_summary(reports)
    _write_corpus_report(reports, args.output_dir)

    return 0 if all(r.success for r in reports) else 2


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Specific PDF file(s) to ingest.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--quiet", action="store_true", help="Only log warnings/errors.")
    return parser.parse_args(argv)


def _resolve_pdf_paths(args: argparse.Namespace) -> list[Path]:
    if args.paths:
        return [p for p in args.paths if p.is_file()]
    if args.input_dir.is_dir():
        return sorted(args.input_dir.glob("*.pdf"))
    return []


def _print_report(report: IngestionReport) -> None:
    status = "OK" if report.success else "FAILED"
    print(
        f"[{status}] {report.paper_id}  "
        f"pages={report.page_count} text_chars={report.total_text_length} "
        f"text_blocks={report.text_block_count} "
        f"sections={report.section_count} figures={report.figure_count} "
        f"tables={report.table_count} citations={report.citation_count} "
        f"warnings={report.warning_count} errors={report.error_count}"
    )
    for issue in report.issues:
        page = f" (page {issue.page})" if issue.page is not None else ""
        print(f"    [{issue.severity}] {issue.stage}{page}: {issue.message}")


def _print_corpus_summary(reports: list[IngestionReport]) -> None:
    succeeded = sum(1 for r in reports if r.success)
    print(
        f"\nCorpus summary: {succeeded}/{len(reports)} succeeded, "
        f"{sum(r.warning_count for r in reports)} warnings, "
        f"{sum(r.error_count for r in reports)} errors."
    )
    print(
        "This reports ingestion completion and structural consistency, not "
        "extraction accuracy - accuracy requires labeled data (see docs/evaluation.md)."
    )


def _write_corpus_report(reports: list[IngestionReport], output_dir: Path) -> None:
    path = output_dir / "_corpus_report.json"
    path.write_text(
        json.dumps([r.model_dump() for r in reports], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
