"""Validation pipeline stage (architecture.md §4.1): builds the IngestionReport and
performs sanity checks beyond what pydantic's field-level validation already covers
(e.g. cross-entity page-range consistency).

This does not claim extraction is correct, only that the produced structure is
internally consistent (schema-valid, in-range page references) — see docs/evaluation.md
for why accuracy claims are out of scope until there's labeled data to check against.
"""

from __future__ import annotations

from src.domain.models.paper import Paper
from src.ingestion.report import IngestionIssue, IngestionReport


def build_report(
    paper: Paper,
    parser_warnings: list[str],
    extra_warnings: list[str] | None = None,
) -> IngestionReport:
    """Build an IngestionReport for a successfully parsed ``paper``.

    ``parser_warnings`` are ``Paper.warnings`` as produced by the parser;
    ``extra_warnings`` are warnings from later pipeline stages (e.g. asset
    persistence) that aren't part of the domain model itself.
    """
    issues: list[IngestionIssue] = [
        IngestionIssue(stage="parsing", severity="warning", message=w)
        for w in parser_warnings
    ]
    issues.extend(
        IngestionIssue(stage="assets", severity="warning", message=w)
        for w in (extra_warnings or [])
    )
    issues.extend(_cross_entity_checks(paper))

    pages_with_issues = [p.page_number for p in paper.pages if p.has_extraction_issue]
    total_text_length = sum(p.text_length for p in paper.pages)

    return IngestionReport(
        paper_id=paper.paper_id,
        source_path=paper.source_path,
        success=True,
        page_count=paper.page_count,
        total_text_length=total_text_length,
        text_block_count=len(paper.text_blocks),
        section_count=len(paper.sections),
        figure_count=len(paper.figures),
        table_count=len(paper.tables),
        citation_count=len(paper.citations),
        pages_with_extraction_issues=pages_with_issues,
        issues=issues,
    )


def build_failure_report(
    paper_id: str, source_path: str, error_message: str
) -> IngestionReport:
    """Build an IngestionReport for a document that failed required extraction
    entirely (parser raised ``ParsingError``/``InvalidDocumentError``)."""
    return IngestionReport(
        paper_id=paper_id,
        source_path=source_path,
        success=False,
        issues=[
            IngestionIssue(stage="parsing", severity="error", message=error_message)
        ],
    )


def _cross_entity_checks(paper: Paper) -> list[IngestionIssue]:
    """Flag page references that fall outside ``[1, page_count]`` — a bug signal,
    not something to silently accept (NFR-006)."""
    issues: list[IngestionIssue] = []

    def _check(page: int | None, entity: str, entity_id: str) -> None:
        if page is not None and not (1 <= page <= paper.page_count):
            issues.append(
                IngestionIssue(
                    stage="validation",
                    severity="error",
                    message=f"{entity} {entity_id} references out-of-range page {page} "
                    f"(document has {paper.page_count} pages)",
                    page=page,
                )
            )

    for block in paper.text_blocks:
        _check(block.page, "text_block", block.block_id)
    for section in paper.sections:
        _check(section.page, "section", section.section_id)
    for figure in paper.figures:
        _check(figure.page, "figure", figure.figure_id)
    for table in paper.tables:
        _check(table.page, "table", table.table_id)
    for citation in paper.citations:
        _check(citation.page, "citation", citation.citation_id)

    return issues
