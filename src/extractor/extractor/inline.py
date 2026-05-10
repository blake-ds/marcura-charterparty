"""Parser for the Shell Additional and Essar Rider sections (inline layout).

Unlike SHELLVOY there is no left-margin title column. Each clause begins with
``N.`` flush against the left edge (x ≈ 50pt) followed by the title on the
same line; the body starts on the following line.

Two real-world wrinkles in this corpus:

1. The clause number is sometimes typeset as the bare digit followed by the
   period glued to the next word (``22 .BILL OF LADING …``). We accept both
   forms — ``N.`` and ``N`` followed by ``.…`` — so the anchor is detected
   either way.
2. A clause may be a single, complete sentence on the anchor's line with no
   subsequent body (e.g. *Essar Rider* clause 16). When the below-line body
   is empty but the anchor line carries substantive content, we promote that
   inline content into ``text`` and leave ``title`` empty — so the clause
   stays in the output instead of being silently dropped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict

from extractor.models import Clause, Section
from extractor.pdf import Char, Page, Word
from extractor.text import chars_to_text

_NUMBER_RE = re.compile(r"^(\d{1,3})\.?$")
_DOT_PREFIX_RE = re.compile(r"^\.(\S.*)?$")

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
    word: Word  # the "N." (or bare "N") token
    title: str  # text after the number on the same line


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
        for line_y, line_words in _group_words_by_line(page.visible_words()):
            anchor = _try_anchor(page, line_words, line_y)
            if anchor is not None:
                anchors.append(anchor)
    return sorted(anchors, key=lambda a: (a.page, a.y))


def _try_anchor(page: Page, line_words: list[Word], line_y: float) -> _Anchor | None:
    """Return an :class:`_Anchor` if the line starts with a clause number."""
    line_words = sorted(line_words, key=lambda w: w.x0)
    first = line_words[0]
    match = _NUMBER_RE.match(first.text)
    if match is None:
        return None
    if not (_CLAUSE_NUMBER_X_MIN <= first.x0 <= _CLAUSE_NUMBER_X_MAX):
        return None

    rest = line_words[1:]
    # Handle the "22" + ".BILL …" split — pull the leading dot off the next
    # word so the title reads as plain prose.
    if not first.text.endswith(".") and rest:
        m = _DOT_PREFIX_RE.match(rest[0].text)
        if m is None:
            return None  # bare digit not followed by ".something" — not an anchor
        cleaned_first = m.group(1) or ""
        title_words = ([cleaned_first] if cleaned_first else []) + [w.text for w in rest[1:]]
    else:
        title_words = [w.text for w in rest]

    title = " ".join(t for t in title_words if t).strip()
    return _Anchor(
        ordinal=int(match.group(1)),
        page=page.number,
        y=line_y,
        word=first,
        title=title,
    )


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
        # Single-line clause: the anchor line itself is the entire clause.
        if anchor.title:
            return Clause(
                section=section,
                ordinal=anchor.ordinal,
                title="",
                text=anchor.title,
                page_start=anchor.page,
                page_end=anchor.page,
            )
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
