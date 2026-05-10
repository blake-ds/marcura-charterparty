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
from pydantic import BaseModel, ConfigDict, computed_field

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

    @computed_field
    @property
    def x_mid(self) -> float:
        return (self.x0 + self.x1) / 2

    @computed_field
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

    @computed_field
    @property
    def x_mid(self) -> float:
        return (self.x0 + self.x1) / 2

    @computed_field
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
