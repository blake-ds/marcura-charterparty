"""Unit tests for :func:`extractor.pdf.line_vote_filter`.

The integration suite (test_pipeline_against_sample) pins the filter against
the real PDF, but the filter has four distinct rules — line-vote, sandwich,
word-level promotion, and the punctuation-led exception — each with its own
threshold. Synthetic :class:`Char` fixtures exercise the rules in isolation
so a regression to the rule logic fails fast, not after a 39-page run.
"""

from __future__ import annotations

from extractor.pdf import Char, line_vote_filter
from extractor.text import chars_to_text


def _line(
    text: str, *, y: float, page: int = 1, x0: float = 50.0, struck: bool = False
) -> list[Char]:
    """Build a list of `Char`s for a string laid out on one line."""
    chars: list[Char] = []
    x = x0
    for ch in text:
        chars.append(Char(text=ch, x0=x, y0=y, x1=x + 5.0, y1=y + 10.0, page=page, struck=struck))
        x += 5.0
    return chars


def _mixed_line(prefix: str, suffix: str, *, y: float, page: int = 1) -> list[Char]:
    """Build a line with a struck prefix followed by a visible suffix."""
    return _line(prefix, y=y, page=page, struck=True) + _line(
        suffix, y=y, page=page, x0=50.0 + len(prefix) * 5.0, struck=False
    )


def test_visible_line_kept_intact() -> None:
    """A fully visible line passes through unchanged."""
    chars = _line("hello world", y=10)
    kept = line_vote_filter(chars)
    assert chars_to_text(kept) == "hello world"


def test_struck_first_majority_struck_line_dropped() -> None:
    """First printable struck *and* >50% struck → line drops entirely."""
    chars = _mixed_line("[STRUCK PREFIX HERE THAT IS LONG] ", "tail", y=20)
    # 33 struck chars + 1 visible space + 4 visible chars = ~88% struck.
    kept = line_vote_filter(chars)
    assert "tail" not in chars_to_text(kept)


def test_first_printable_visible_keeps_line_regardless_of_ratio() -> None:
    """Even >50% struck, line is kept when the first printable char is visible.

    Locks the additional-3 case: ``for the duration of this Charter. [STRUCK
    Owners shall furnish H & M policy cover note.]`` — visible content opens
    the line, struck replacement on the right.
    """
    visible = _line("kept text. ", y=30, x0=50.0)
    struck = _line("STRUCK REPLACEMENT", y=30, x0=120.0, struck=True)
    kept = line_vote_filter(visible + struck)
    assert "kept text." in chars_to_text(kept)
    assert "STRUCK" not in chars_to_text(kept)


def test_word_level_promotion_drops_partial_strike_word() -> None:
    """Word with any struck glyph → drop whole word (indemnity → "demnity")."""
    in_chars = _line("in", y=40, x0=50.0, struck=True)
    demnity_chars = _line("demnity follows", y=40, x0=60.0, struck=False)
    kept = line_vote_filter(in_chars + demnity_chars)
    # "indemnity" → all chars struck or part-struck-word → both halves dropped together
    text = chars_to_text(kept)
    assert "demnity" not in text  # the orphan suffix is not emitted
    assert "follows" in text  # the next visible whole word survives


def test_punctuation_led_visible_tail_kept() -> None:
    """``[STRUCK item, item], Worldscale charges / dues;`` — visible tail opening
    with punctuation must be kept even when the line is >50% struck."""
    struck = _line("a long struck list of items here", y=50, struck=True)
    visible_tail = _line(", Worldscale charges / dues;", y=50, x0=50.0 + 32 * 5.0)
    kept = line_vote_filter(struck + visible_tail)
    assert "Worldscale charges / dues;" in chars_to_text(kept)


def test_sandwich_drops_low_strike_line_between_struck_neighbours() -> None:
    """Clean-ish line sandwiched between two heavy lines on the same page →
    dropped. Locks the *VGO Cleaning Clause* pattern where a strike rectangle
    happens to end short of the full line."""
    above = _line("HEAVY STRUCK LINE ABOVE THE FRAGMENT", y=100, struck=True)
    fragment_struck_prefix = _line("B.Flush", y=114, x0=50.0, struck=True)
    fragment_visible_tail = _line("pumps and lines including decks", y=114, x0=85.0)
    below = _line("HEAVY STRUCK LINE BELOW THE FRAGMENT", y=128, struck=True)
    kept = line_vote_filter(above + fragment_struck_prefix + fragment_visible_tail + below)
    assert "pumps and lines" not in chars_to_text(kept)


def test_blank_lines_are_not_sandwich_anchors() -> None:
    """Blank lines (no printable glyphs) are vertical spacing, not struck content.

    Locks shellvoy-41's regression: ``Owners warrant that throughout the
    duration of this Charter the vessel will be:`` had blank lines above and
    below — those must not flag the visible line as sandwiched.
    """
    above = _line("ITOPF Clause", y=200)
    blank_above = []  # truly empty between ITOPF and the body line
    body = _line("Owners warrant that throughout the duration", y=214)
    blank_below = []  # blank again
    below = _line("i) owned or demise chartered", y=230)
    kept = line_vote_filter(above + blank_above + body + blank_below + below)
    text = chars_to_text(kept)
    assert "Owners warrant that throughout the duration" in text


def test_cross_page_neighbours_do_not_trigger_sandwich() -> None:
    """Sandwich only fires within a single page — different pages never anchor."""
    p1_struck = _line("STRUCK CONTENT ON PAGE 1", y=700, page=1, struck=True)
    p2_low_strike = _mixed_line("[short] ", "visible content here", y=20, page=2)
    p2_clean = _line("clean visible line on page 2", y=34, page=2)
    kept = line_vote_filter(p1_struck + p2_low_strike + p2_clean)
    text = chars_to_text(kept)
    # The mid-line "visible content here" survives because page-2's neighbour
    # below it is clean, and page 1's struck line is on a different page.
    assert "visible content here" in text
