"""Parser for the Shell Additional and Essar Rider sections (inline layout).

Unlike SHELLVOY there is no left-margin title column. Each clause begins with
``N.`` flush against the left edge (x ≈ 50pt) followed by the title on the
same line; the body starts on the following line.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from extractor.models import Clause, Section
from extractor.pdf import Char, Page, Word
from extractor.text import chars_to_text

_CLAUSE_NUMBER_RE = re.compile(r"^(\d{1,3})\.$")

_CLAUSE_NUMBER_X_MIN = 40.0
_CLAUSE_NUMBER_X_MAX = 110.0
_BODY_X_MIN = 30.0
_BODY_X_MAX = 580.0
_TITLE_LINE_TOLERANCE = 5.0  # glyphs within this many points of the anchor are part of the title


class _Anchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    ordinal: int
    page: int
    y: float
    word: Word  # the "N." token
    title: str  # everything else on the anchor's line


def parse(pages: tuple[Page, ...], section: Section) -> list[Clause]:
    """Parse inline-layout pages (Additional / Rider) into clauses."""
    anchors = _find_anchors(pages)
    clauses: list[Clause] = []
    for index, anchor in enumerate(anchors):
        next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
        clause = _build_clause(pages, anchor, next_anchor, section)
        if clause is not None:
            clauses.append(clause)
    return clauses


def _find_anchors(pages: tuple[Page, ...]) -> list[_Anchor]:
    anchors: list[_Anchor] = []
    for page in pages:
        lines = _group_words_by_line(page.visible_words())
        for y, line_words in lines:
            line_words = sorted(line_words, key=lambda w: w.x0)
            first = line_words[0]
            match = _CLAUSE_NUMBER_RE.match(first.text)
            if match is None:
                continue
            if not (_CLAUSE_NUMBER_X_MIN <= first.x0 <= _CLAUSE_NUMBER_X_MAX):
                continue
            title = " ".join(w.text for w in line_words[1:]).strip()
            anchors.append(
                _Anchor(
                    ordinal=int(match.group(1)),
                    page=page.number,
                    y=y,
                    word=first,
                    title=title,
                )
            )
    anchors.sort(key=lambda a: (a.page, a.y))
    return anchors


def _group_words_by_line(words: Iterable[Word]) -> list[tuple[float, list[Word]]]:
    buckets: dict[int, list[Word]] = {}
    for word in words:
        ly = round(word.y_mid)
        for existing_y in buckets:
            if abs(existing_y - ly) <= 2:
                buckets[existing_y].append(word)
                break
        else:
            buckets[ly] = [word]
    return sorted(buckets.items())


def _build_clause(
    pages: tuple[Page, ...],
    anchor: _Anchor,
    next_anchor: _Anchor | None,
    section: Section,
) -> Clause | None:
    end_page = pages[-1].number if next_anchor is None else next_anchor.page
    end_y = float("inf") if next_anchor is None else next_anchor.y

    body_chars = list(_collect_body_chars(pages, anchor, end_page, end_y))
    text = chars_to_text(body_chars)
    if not text:
        return None

    return Clause(
        section=section,
        ordinal=anchor.ordinal,
        title=anchor.title,
        text=text,
        page_start=anchor.page,
        page_end=max(anchor.page, end_page),
    )


def _collect_body_chars(
    pages: tuple[Page, ...], anchor: _Anchor, end_page: int, end_y: float
) -> list[Char]:
    chars: list[Char] = []
    for page in pages:
        if page.number < anchor.page or page.number > end_page:
            continue
        for char in page.visible_chars():
            if not (_BODY_X_MIN < char.x_mid < _BODY_X_MAX):
                continue
            if not _within_clause_range(char, anchor, end_page, end_y):
                continue
            chars.append(char)
    return chars


def _within_clause_range(char: Char, anchor: _Anchor, end_page: int, end_y: float) -> bool:
    if char.page == anchor.page and char.y_mid <= anchor.y + _TITLE_LINE_TOLERANCE:
        return False  # skip the anchor's own line (carries title, not body)
    return not (char.page == end_page and char.y_mid >= end_y - _TITLE_LINE_TOLERANCE)
