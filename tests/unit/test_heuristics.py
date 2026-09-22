"""Unit tests for the pure heuristics used by PyMuPDFDocumentParser — exercised with
plain Python data so they don't require a real PDF (see heuristics.py docstring)."""

from __future__ import annotations

from src.infrastructure.parsers.heuristics import (
    TextSpan,
    find_nearby_caption,
    guess_title_and_authors,
    is_figure_caption,
    is_heading_candidate,
    is_references_heading,
    is_table_caption,
    split_author_line,
    split_reference_entries,
)


def test_heading_candidate_detects_larger_font() -> None:
    spans = [TextSpan(text="Introduction", size=16.0, bold=False)]
    assert is_heading_candidate("Introduction", spans, median_size=10.0)


def test_heading_candidate_detects_numbered_heading_even_at_body_font_size() -> None:
    spans = [TextSpan(text="2.1 Related Work", size=10.0, bold=False)]
    assert is_heading_candidate("2.1 Related Work", spans, median_size=10.0)


def test_heading_candidate_rejects_long_body_paragraph() -> None:
    long_text = "This is a long paragraph of body text that goes on and on. " * 3
    spans = [TextSpan(text=long_text, size=10.0, bold=False)]
    assert not is_heading_candidate(long_text, spans, median_size=10.0)


def test_heading_candidate_rejects_empty_line() -> None:
    assert not is_heading_candidate("   ", [], median_size=10.0)


def test_guess_title_and_authors_picks_largest_font_line() -> None:
    lines = [
        ("A Great Paper About Things", 18.0),
        ("Jane Doe, John Smith", 11.0),
        ("Abstract", 12.0),
        ("This paper studies things.", 10.0),
    ]
    title, author_line = guess_title_and_authors(lines)
    assert title == "A Great Paper About Things"
    assert author_line == "Jane Doe, John Smith"


def test_guess_title_and_authors_returns_none_for_empty_page() -> None:
    assert guess_title_and_authors([]) == (None, None)


def test_split_author_line_handles_commas_and_and() -> None:
    assert split_author_line("Jane Doe, John Smith and Alice Lee") == [
        "Jane Doe",
        "John Smith",
        "Alice Lee",
    ]


def test_split_author_line_strips_footnote_markers() -> None:
    assert split_author_line("Jane Doe*, John Smith†") == ["Jane Doe", "John Smith"]


def test_split_author_line_empty_input_returns_empty_list() -> None:
    assert split_author_line("") == []
    assert split_author_line("   ") == []


def test_find_nearby_caption_matches_below_target() -> None:
    target_bbox = (0.0, 100.0, 200.0, 200.0)
    lines = [
        ("Figure 1: A nice plot.", (0.0, 205.0, 200.0, 215.0)),
        ("Unrelated text far away", (0.0, 500.0, 200.0, 510.0)),
    ]
    caption = find_nearby_caption(target_bbox, lines, is_figure_caption)
    assert caption == "Figure 1: A nice plot."


def test_find_nearby_caption_returns_none_when_nothing_matches() -> None:
    target_bbox = (0.0, 100.0, 200.0, 200.0)
    lines = [("Just some body text", (0.0, 205.0, 200.0, 215.0))]
    assert find_nearby_caption(target_bbox, lines, is_figure_caption) is None


def test_is_table_caption_matches_table_prefix() -> None:
    assert is_table_caption("Table 2: Results on the benchmark.")
    assert not is_table_caption("Figure 2: Results on the benchmark.")


def test_is_references_heading_matches_standalone_heading_only() -> None:
    assert is_references_heading("References")
    assert is_references_heading("Bibliography")
    assert not is_references_heading("References [1] is a great paper")


def test_split_reference_entries_splits_numbered_markers() -> None:
    blob = "[1] A. Author. Paper One. 2020.\n[2] B. Author. Paper Two. 2021."
    entries = split_reference_entries(blob)
    assert len(entries) == 2
    assert entries[0] == ("[1] A. Author. Paper One. 2020.", "1")
    assert entries[1] == ("[2] B. Author. Paper Two. 2021.", "2")


def test_split_reference_entries_falls_back_to_single_entry_when_unrecognized() -> None:
    blob = "Some reference text\nwith no recognizable markers at all"
    entries = split_reference_entries(blob)
    assert len(entries) == 1
    assert entries[0][1] is None


def test_split_reference_entries_empty_input() -> None:
    assert split_reference_entries("") == []
