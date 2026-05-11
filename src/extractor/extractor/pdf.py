"""PyMuPDF-backed character extraction with strike-through filtering.

The source PDF encodes strike-through as **thin filled rectangles** drawn over
the text — not as PDF annotations and not as a font flag. We expose two pieces
of information per character: its bbox geometry and whether a strike rectangle
covers its centre point. Downstream filtering then becomes a single attribute
check (``char.struck``) instead of bbox arithmetic scattered across modules.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pymupdf
from pydantic import BaseModel, ConfigDict

# Empirical thresholds derived from the SHELLVOY 5 sample. The strike rectangles
# in this corpus are ≈0.42pt tall and span the full strike line; anything taller
# than ~2pt is a layout block, not a strike.
_STRIKE_HEIGHT_MAX = 2.0
_STRIKE_WIDTH_MIN = 5.0
_STRIKE_Y_TOLERANCE = 1.0  # how far above/below the rect a struck glyph may sit
_STRIKE_X_TOLERANCE = 0.5


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Char(_Frozen):
    """A single glyph with its page geometry and strike-through verdict."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int  # 1-indexed
    struck: bool

    @property
    def x_mid(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y_mid(self) -> float:
        return (self.y0 + self.y1) / 2


class StrikeRect(_Frozen):
    """The on-page rectangle that strikes through one or more glyphs."""

    x0: float
    y0: float
    x1: float
    y1: float


class Word(_Frozen):
    """A whitespace-delimited token, with bbox and an aggregate strike verdict."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    struck: bool

    @property
    def x_mid(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def y_mid(self) -> float:
        return (self.y0 + self.y1) / 2


class Page(_Frozen):
    """Everything the parser needs from one rendered page."""

    number: int  # 1-indexed
    chars: tuple[Char, ...]
    words: tuple[Word, ...]
    strikes: tuple[StrikeRect, ...]
    width: float
    height: float

    def visible_chars(self) -> tuple[Char, ...]:
        return tuple(c for c in self.chars if not c.struck)

    def visible_words(self) -> tuple[Word, ...]:
        return tuple(w for w in self.words if not w.struck)


def load_pages(pdf_path: Path) -> tuple[Page, ...]:
    """Read every page of ``pdf_path`` into ``Page`` records."""
    doc = pymupdf.open(str(pdf_path))
    try:
        return tuple(_load_page(doc[i], page_number=i + 1) for i in range(doc.page_count))
    finally:
        doc.close()


_LINE_VOTE_STRIKE_RATIO = 0.5


_LINE_SANDWICH_GAP = 30.0  # max y-gap to count an adjacent line as a sandwich neighbour
_LINE_HEAVY_RATIO = 0.75  # struck ratio at which a line is "heavy enough" to anchor a sandwich


def line_vote_filter(chars: Iterable[Char]) -> list[Char]:
    """Drop fragments left over from partial strike rectangles.

    Three cleanup passes operate on every glyph (struck + visible) for a
    candidate body region:

    1. **Position-aware whole-line vote.** A line is "unsafe" when its
       left-most printable glyph is struck *and* the line is
       >``_LINE_VOTE_STRIKE_RATIO`` struck overall, *unless* the first
       visible non-whitespace glyph is punctuation (the line opens with a
       comma or colon — a clean continuation tail, e.g. ``[STRUCK item,
       item], Worldscale charges / dues;``).
    2. **Sandwich rule.** A line that doesn't trip the rule above but sits
       tightly (≤``_LINE_SANDWICH_GAP`` between adjacent line y values)
       between two unsafe-or-heavy lines on the same page is *also* unsafe.
       Without this, a single low-strike line in the middle of a wholly
       struck clause body ("pumps and lines including … " in a
       wholly-replaced VGO cleaning clause where the original line happens
       to have only a short ``B.Flush`` prefix under its strike rect) would
       leak the original struck content into the JSON.
    3. **Word-level promotion + whitespace fidelity.** On the kept lines, a
       word with *any* struck glyph is dropped whole (catches indemnity →
       "demnity" / company → "y" / Whether → "ther"); whitespace glyphs are
       emitted only when visible in the PDF, preserving spacing without
       dragging in struck spaces.
    """
    by_line: dict[tuple[int, int], list[Char]] = {}
    for char in chars:
        by_line.setdefault((char.page, round(char.y_mid)), []).append(char)

    lines = sorted(by_line.items())  # ((page, y), [chars]) sorted globally

    unsafe = [_line_is_unsafe(line_chars) for _, line_chars in lines]
    _apply_sandwich(lines, unsafe)

    kept: list[Char] = []
    for is_unsafe, (_, line_chars) in zip(unsafe, lines, strict=True):
        if is_unsafe:
            continue
        kept.extend(_keep_clean_words(sorted(line_chars, key=lambda c: c.x0)))
    return kept


def _line_is_unsafe(line_chars: list[Char]) -> bool:
    sorted_chars = sorted(line_chars, key=lambda c: c.x0)
    printable = [c for c in sorted_chars if c.text.strip()]
    if not printable:
        return False  # blank line is harmless
    if not printable[0].struck:
        return False  # visible-first → never unsafe
    struck_ratio = sum(1 for c in printable if c.struck) / len(printable)
    if struck_ratio <= _LINE_VOTE_STRIKE_RATIO:
        return False
    # Punctuation-led exception: visible tail begins with `,` / `:` etc.
    first_visible_nonspace = next(
        (c for c in sorted_chars if not c.struck and c.text.strip()), None
    )
    if first_visible_nonspace is None:
        return True
    return first_visible_nonspace.text.isalnum()


def _apply_sandwich(lines: list[tuple[tuple[int, int], list[Char]]], unsafe: list[bool]) -> None:
    """Mark a line unsafe if its tight neighbours are unsafe too.

    Two-pass: first the immediate-neighbour sweep, then one expansion pass so
    a chain of contaminated lines propagates (B is sandwiched by A & C; C is
    then sandwiched by B & D → C unsafe via the second pass). We use the
    pre-sandwich ``unsafe`` flag as the seed plus :func:`_line_heavy_struck`
    (≥``_LINE_HEAVY_RATIO`` struck) so a single low-strike fragment in the
    middle of a wholly struck clause body is correctly suppressed.
    """
    heavy = [_line_heavy_struck(line_chars) for _, line_chars in lines]
    seed = [a or b for a, b in zip(unsafe, heavy, strict=True)]
    # Two passes lets sandwich propagate through a tight block of fragments.
    for _ in range(2):
        for index in range(1, len(lines) - 1):
            if unsafe[index]:
                continue
            (cur_page, cur_y), _ = lines[index]
            (prev_page, prev_y), _ = lines[index - 1]
            (next_page, next_y), _ = lines[index + 1]
            if cur_page != prev_page or cur_page != next_page:
                continue
            if (cur_y - prev_y) > _LINE_SANDWICH_GAP or (next_y - cur_y) > _LINE_SANDWICH_GAP:
                continue
            if seed[index - 1] and seed[index + 1]:
                unsafe[index] = True
                seed[index] = True


def _line_heavy_struck(line_chars: list[Char]) -> bool:
    """`≥_LINE_HEAVY_RATIO` struck — a sandwich anchor.

    A blank line (no printable glyphs at all) is *not* heavy — it's vertical
    spacing between paragraphs, not struck content. Treating it as heavy was
    the bug that swallowed the ``Owners warrant that throughout the duration
    of this Charter the vessel will be:`` line of shellvoy-41's replacement.

    The threshold catches anchor rows of wholly-replaced clauses (e.g. ``34.``
    alone visible while the rest of *Canada Clause*'s title is struck) — those
    rows must count as sandwich anchors so the surviving mid-clause fragments
    below them get filtered out.
    """
    printable = [c for c in line_chars if c.text.strip()]
    if not printable:
        return False
    struck_ratio = sum(1 for c in printable if c.struck) / len(printable)
    return struck_ratio >= _LINE_HEAVY_RATIO


def _keep_clean_words(line_chars: list[Char]) -> list[Char]:
    """Return only fully-visible words on a line (drop partial-strike fragments)."""
    line_chars = sorted(line_chars, key=lambda c: c.x0)
    out: list[Char] = []
    word_buffer: list[Char] = []
    for char in line_chars:
        if not char.text.strip():
            if word_buffer:
                if not any(c.struck for c in word_buffer):
                    out.extend(word_buffer)
                word_buffer = []
            if not char.struck:
                out.append(char)
            continue
        word_buffer.append(char)
    if word_buffer and not any(c.struck for c in word_buffer):
        out.extend(word_buffer)
    return out


def _load_page(mu_page: pymupdf.Page, *, page_number: int) -> Page:
    strikes = _detect_strike_rects(mu_page)
    chars = tuple(_iter_chars(mu_page, page_number=page_number, strikes=strikes))
    words = tuple(_iter_words(mu_page, page_number=page_number, strikes=strikes))
    return Page(
        number=page_number,
        chars=chars,
        words=words,
        strikes=strikes,
        width=mu_page.rect.width,
        height=mu_page.rect.height,
    )


def _detect_strike_rects(mu_page: pymupdf.Page) -> tuple[StrikeRect, ...]:
    """Return every drawing rectangle that looks like a strike-through line."""
    rects: list[StrikeRect] = []
    for drawing in mu_page.get_drawings():
        for item in drawing["items"]:
            if item[0] != "re":
                continue
            rect = item[1]
            if rect.height < _STRIKE_HEIGHT_MAX and rect.width > _STRIKE_WIDTH_MIN:
                rects.append(StrikeRect(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1))
    return tuple(rects)


def _iter_chars(
    mu_page: pymupdf.Page, *, page_number: int, strikes: tuple[StrikeRect, ...]
) -> Iterable[Char]:
    for block in mu_page.get_text("rawdict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                for ch in span["chars"]:
                    x0, y0, x1, y1 = ch["bbox"]
                    x_mid = (x0 + x1) / 2
                    y_mid = (y0 + y1) / 2
                    yield Char(
                        text=ch["c"],
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        page=page_number,
                        struck=_is_struck(x_mid, y_mid, strikes),
                    )


def _is_struck(x_mid: float, y_mid: float, strikes: tuple[StrikeRect, ...]) -> bool:
    for r in strikes:
        if (
            r.y0 - _STRIKE_Y_TOLERANCE < y_mid < r.y1 + _STRIKE_Y_TOLERANCE
            and r.x0 - _STRIKE_X_TOLERANCE < x_mid < r.x1 + _STRIKE_X_TOLERANCE
        ):
            return True
    return False


def _iter_words(
    mu_page: pymupdf.Page, *, page_number: int, strikes: tuple[StrikeRect, ...]
) -> Iterable[Word]:
    for raw in mu_page.get_text("words"):
        x0, y0, x1, y1, text = raw[0], raw[1], raw[2], raw[3], raw[4]
        yield Word(
            text=text,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            page=page_number,
            struck=_word_struck(x0, y0, x1, y1, strikes),
        )


def _word_struck(
    x0: float, y0: float, x1: float, y1: float, strikes: tuple[StrikeRect, ...]
) -> bool:
    """A word is struck if a strike rectangle covers ≥50% of its width."""
    word_width = max(x1 - x0, 1e-3)
    y_mid = (y0 + y1) / 2
    overlap = 0.0
    for r in strikes:
        if r.y0 - _STRIKE_Y_TOLERANCE < y_mid < r.y1 + _STRIKE_Y_TOLERANCE:
            overlap += max(0.0, min(r.x1, x1) - max(r.x0, x0))
    return (overlap / word_width) >= 0.5
