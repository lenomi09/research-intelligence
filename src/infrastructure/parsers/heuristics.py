"""Pure, PyMuPDF-independent heuristics used by ``PyMuPDFDocumentParser``.

Kept separate from ``pymupdf_parser.py`` so they can be unit-tested with plain
Python data (spans/blocks as dicts/tuples) instead of a real PDF — see
tests/unit/test_heuristics.py. None of this is a claim of accuracy: every function
here is a best-effort guess and says so in its docstring (see docs/decisions.md
ADR-014 for the accepted limitations).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

_HEADING_KEYWORDS = {
    "abstract",
    "introduction",
    "related work",
    "background",
    "method",
    "methods",
    "methodology",
    "approach",
    "experiment",
    "experiments",
    "experimental setup",
    "results",
    "discussion",
    "conclusion",
    "conclusions",
    "limitations",
    "acknowledgements",
    "acknowledgments",
    "references",
    "bibliography",
    "appendix",
}

_NUMBERED_HEADING_RE = re.compile(r"^\s*(\d{1,2}(\.\d{1,2})*)\.?\s+\S")

_REFERENCE_HEADING_RE = re.compile(r"^\s*(references|bibliography)\s*$", re.IGNORECASE)

_FIGURE_CAPTION_RE = re.compile(r"^\s*fig(ure)?\.?\s*\d+", re.IGNORECASE)
_TABLE_CAPTION_RE = re.compile(r"^\s*table\s*\d+", re.IGNORECASE)

# Matches a leading reference marker: "[12]", "12.", "12)" at the start of a line.
_REFERENCE_ENTRY_START_RE = re.compile(r"^\s*(?:\[(\d{1,4})\]|(\d{1,4})[.)])\s+")


@dataclass(frozen=True)
class TextSpan:
    """A minimal, parser-agnostic view of one PyMuPDF text span."""

    text: str
    size: float
    bold: bool


def is_heading_candidate(line_text: str, spans: list[TextSpan], median_size: float) -> bool:
    """Best-effort guess: is this line a section heading?

    True when the line is short and either (a) its font is notably larger than the
    page's median body-text size, (b) it is bold, or (c) it matches a numbered-heading
    pattern ("1. Introduction") or a common section keyword — this catches
    camera-ready papers where heading/body font sizes are nearly identical.
    """
    stripped = line_text.strip()
    if not stripped or len(stripped) > 80:
        return False
    if not spans:
        return False

    max_size = max(s.size for s in spans)
    any_bold = any(s.bold for s in spans)
    larger_font = median_size > 0 and max_size >= median_size * 1.15
    numbered = bool(_NUMBERED_HEADING_RE.match(stripped))
    keyword_match = stripped.lower().rstrip(".:").strip() in _HEADING_KEYWORDS

    return bool(larger_font or any_bold or numbered or keyword_match)


def guess_title_and_authors(
    first_page_lines: list[tuple[str, float]],
) -> tuple[str | None, str | None]:
    """Guess (title, raw_author_line) from page-1 lines as (text, max_font_size) pairs.

    Heuristic: the title is the line with the largest font size in the first few
    lines of the page; the author line is the next non-empty line after it, if any.
    Returns ``(None, None)`` when the page has no usable lines — callers must not
    fabricate a title/author from an empty guess (NFR-006).
    """
    candidates = [(text, size) for text, size in first_page_lines if text.strip()][:12]
    if not candidates:
        return None, None

    title_index = max(range(len(candidates)), key=lambda i: candidates[i][1])
    title = candidates[title_index][0].strip()

    author_line: str | None = None
    if title_index + 1 < len(candidates):
        author_line = candidates[title_index + 1][0].strip()

    return title, author_line


def split_author_line(raw: str) -> list[str]:
    """Split a raw author line like "Jane Doe, John Smith" into individual names.

    Best-effort: splits on commas/"and"/semicolons and strips common footnote
    markers (†, *, superscript digits). Returns an empty list for input that doesn't
    look like a name list, rather than guessing.
    """
    if not raw or not raw.strip():
        return []
    cleaned = re.sub(r"[\*†‡0-9,]*$", "", raw.strip())
    parts = re.split(r",|\band\b|;", cleaned)
    names = []
    for part in parts:
        name = re.sub(r"[\*†‡\d]+", "", part).strip()
        if name:
            names.append(name)
    return names


def find_nearby_caption(
    target_bbox: tuple[float, float, float, float],
    page_lines: list[tuple[str, tuple[float, float, float, float]]],
    matches: Callable[[str], bool],
    max_distance: float = 60.0,
) -> str | None:
    """Find a caption line satisfying ``matches`` near ``target_bbox`` on the same page.

    Searches lines below the target first (the common case for figures), then above
    (the common case for tables), within ``max_distance`` PDF points. Returns ``None``
    if nothing matches — a missing caption is left unset, never invented (NFR-006).

    A small ``overlap_tolerance`` allows for text baseline/ascent making a caption
    line's reported bounding box start slightly above the image's bottom edge (a
    normal PyMuPDF quirk, not a sign the line isn't really "below" the image).
    """
    _, y0, _, y1 = target_bbox
    overlap_tolerance = 20.0

    below = [
        (text, bbox)
        for text, bbox in page_lines
        if bbox[1] >= y1 - overlap_tolerance and bbox[1] - y1 <= max_distance
    ]
    above = [
        (text, bbox)
        for text, bbox in page_lines
        if bbox[3] <= y0 + overlap_tolerance and y0 - bbox[3] <= max_distance
    ]

    for candidates in (sorted(below, key=lambda t: t[1][1]), sorted(above, key=lambda t: -t[1][3])):
        for text, _ in candidates:
            if matches(text.strip()):
                return text.strip()
    return None


def is_figure_caption(text: str) -> bool:
    return bool(_FIGURE_CAPTION_RE.match(text.strip()))


def is_table_caption(text: str) -> bool:
    return bool(_TABLE_CAPTION_RE.match(text.strip()))


def is_references_heading(text: str) -> bool:
    return bool(_REFERENCE_HEADING_RE.match(text.strip()))


def split_reference_entries(references_text: str) -> list[tuple[str, str | None]]:
    """Split a references-section blob into ``(raw_text, marker)`` entries.

    Best-effort: looks for lines starting with "[N]" or "N." markers and treats each
    as the start of a new entry. If fewer than 2 entries are found (the heuristic
    didn't recognize the format), the whole blob is returned as a single entry with
    no marker, rather than guessing a split that's likely wrong (NFR-006) — callers
    should treat that case as low-confidence and log a warning.
    """
    lines = [ln for ln in references_text.splitlines() if ln.strip()]
    if not lines:
        return []

    entries: list[list[str]] = []
    markers: list[str | None] = []
    for line in lines:
        match = _REFERENCE_ENTRY_START_RE.match(line)
        if match:
            marker = match.group(1) or match.group(2)
            entries.append([line])
            markers.append(marker)
        elif entries:
            entries[-1].append(line)
        else:
            entries.append([line])
            markers.append(None)

    if len(entries) < 2:
        return [(references_text.strip(), None)]

    return [(" ".join(lines).strip(), marker) for lines, marker in zip(entries, markers)]
