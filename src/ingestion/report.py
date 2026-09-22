"""Per-paper ingestion outcome — the "Validation" stage output (architecture.md §4.1).

Kept in src/ingestion rather than src/domain/models because it describes an ingestion
*run*, not a paper-domain entity other capabilities consume (unlike Paper, Figure,
etc. — see architecture.md §7).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IssueSeverity = Literal["warning", "error"]


class IngestionIssue(BaseModel):
    stage: str
    severity: IssueSeverity
    message: str
    page: int | None = None


class IngestionReport(BaseModel):
    """Summary of one document's ingestion run, for debugging and future evaluation.

    ``success`` is true only when the *required* extraction stage (parsing + text)
    succeeded; optional-stage failures (figures/tables/citations/sections) do not
    flip this to false, but are recorded in ``issues`` so nothing is silently lost
    (NFR-006). This is deliberately not a claim of extraction *accuracy* — see
    docs/evaluation.md for why accuracy claims require labeled data this sprint
    doesn't produce.
    """

    paper_id: str
    source_path: str
    success: bool
    page_count: int = 0
    total_text_length: int = 0
    text_block_count: int = 0
    section_count: int = 0
    figure_count: int = 0
    table_count: int = 0
    citation_count: int = 0
    pages_with_extraction_issues: list[int] = Field(default_factory=list)
    issues: list[IngestionIssue] = Field(default_factory=list)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")
