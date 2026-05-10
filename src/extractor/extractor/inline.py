"""Parser for the Shell Additional and Essar Rider sections (inline layout).

Unlike SHELLVOY there is no left-margin title column. Each clause begins with
``N.`` flush against the left edge (x ≈ 50pt) followed by the title on the
same line; the body starts on the following line.

Two real-world wrinkles in this corpus:

1. The clause number is sometimes typeset as the bare digit followed by the
   period glued to the next word (``22 .BILL OF LADING …``). We accept both
   forms — ``N.`` and ``N`` followed by ``.…`` — so the anchor is detected
   either way.
2. Struck clause headings still matter as **boundaries**. We detect anchors
   from all words, not only visible words, and then decide separately whether
   the clause has enough unstruck content to emit.
3. A clause may be a single, complete sentence on the anchor's line with no
   subsequent body (e.g. *Essar Rider* clause 16). When the below-line body
   is empty but the anchor line carries substantive content, we promote that
   inline content into ``text`` and leave ``title`` empty.
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
    title: str  # text after the number on the same line
    struck: bool


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
        # Use raw words so fully struck clauses still stop the previous clause.
        for line_y, line_words in _group_words_by_line(page.words):
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
        title_words = ([cleaned_first] if cleaned_first else []) + [
            w.text for w in rest[1:] if not w.struck
        ]
    else:
        title_words = [w.text for w in rest if not w.struck]

    title = " ".join(t for t in title_words if t).strip()
    return _Anchor(
        ordinal=int(match.group(1)),
        page=page.number,
        y=line_y,
        title=title,
        struck=first.struck,
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


_MEANINGFUL_TITLE_RE = re.compile(r"[A-Za-z]{2,}")
_BODYISH_TITLE_STARTS = (
    "all voyage ",
    "if ",
    "owners ",
    "charterers ",
    "bill(s) ",
)


def _build_clause(
    pages: tuple[Page, ...],
    anchor: _Anchor,
    next_anchor: _Anchor | None,
    section: Section,
) -> Clause | None:
    """Materialize a clause, classifying the anchor's inline content.

    Three cases differ by the anchor line and whether body text exists below it:

    * **Struck anchor** — boundary only, never emitted.
    * **Heading + body** — ``anchor.title`` looks like a clause heading and
      body lines follow.
    * **Single-line / wrapped sentence** — the anchor line is substantive body
      text, not a heading. We put it into ``text`` and leave ``title`` empty.
    """
    if anchor.struck:
        return None

    end_page = pages[-1].number if next_anchor is None else next_anchor.page
    end_y = float("inf") if next_anchor is None else next_anchor.y

    body_chars = list(_collect_body_chars(pages, anchor, end_page, end_y))
    body_text = chars_to_text(body_chars)

    title = anchor.title if _MEANINGFUL_TITLE_RE.search(anchor.title) else ""
    page_end = max(anchor.page, end_page) if body_text else anchor.page
    heading = _looks_like_heading(title)

    if not body_text:
        if not title:
            return None
        if heading:
            return Clause(
                section=section,
                ordinal=anchor.ordinal,
                title=title,
                text="",
                page_start=anchor.page,
                page_end=anchor.page,
            )
        return Clause(
            section=section,
            ordinal=anchor.ordinal,
            title="",
            text=title,
            page_start=anchor.page,
            page_end=anchor.page,
        )

    if title and not heading:
        return Clause(
            section=section,
            ordinal=anchor.ordinal,
            title="",
            text=f"{title} {body_text}",
            page_start=anchor.page,
            page_end=page_end,
        )

    return Clause(
        section=section,
        ordinal=anchor.ordinal,
        title=title,
        text=body_text,
        page_start=anchor.page,
        page_end=page_end,
    )


def _looks_like_heading(title: str) -> bool:
    if not title:
        return False
    normalized = " ".join(title.split())
    lower = normalized.casefold()
    if lower.startswith(_BODYISH_TITLE_STARTS):
        return False
    if "clause" in lower or "warranty" in lower:
        return True
    if len(normalized) > 80:
        return False
    letters = [ch for ch in normalized if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.65:
        return True
    # Short title-case headings such as "Questionnaire(s)".
    first_alpha = next((ch for ch in normalized if ch.isalpha()), "")
    return bool(first_alpha and first_alpha.isupper() and not normalized.endswith("."))


def _collect_body_chars(
    pages: tuple[Page, ...], anchor: _Anchor, end_page: int, end_y: float
) -> list[Char]:
    """All body glyphs (struck + visible) in the clause's y-range; strike-filtered."""
    candidates: list[Char] = []
    for page in pages:
        if page.number < anchor.page or page.number > end_page:
            continue
        for char in page.chars:
            if not (_BODY_X_MIN < char.x_mid < _BODY_X_MAX):
                continue
            if not _within_clause_range(char, anchor, end_page, end_y):
                continue
            candidates.append(char)
    return _filter_inline_body(candidates)


def _filter_inline_body(chars: list[Char]) -> list[Char]:
    """Keep clean visual lines and discard strike-through debris.

    A mostly struck line or a line whose leading word was struck is unsafe: the
    remaining visible text is often a tail such as "demnity". Low-level edits in
    the middle of a line are kept (e.g. ``ninety (90)`` replaced by ``120``).
    One extra pass drops a clean-looking line when it is sandwiched between
    struck lines in the same tight block; those are continuation lines of a
    struck paragraph.
    """
    lines = _lines(chars)
    if not lines:
        return []

    unsafe = [_line_has_strike(line_chars) for _, line_chars in lines]
    for index, ((page, y), _) in enumerate(lines):
        prev_tight = (
            index > 0 and lines[index - 1][0][0] == page and y - lines[index - 1][0][1] <= 16
        )
        next_tight = (
            index + 1 < len(lines)
            and lines[index + 1][0][0] == page
            and lines[index + 1][0][1] - y <= 16
        )
        sandwiched = prev_tight and next_tight and unsafe[index - 1] and unsafe[index + 1]
        if not unsafe[index] and sandwiched:
            unsafe[index] = True

    kept: list[Char] = []
    for keep_out, (_, line_chars) in zip(unsafe, lines, strict=True):
        if keep_out:
            continue
        kept.extend(_visible_chars_for_kept_line(line_chars))
    return kept


def _visible_chars_for_kept_line(chars: list[Char]) -> list[Char]:
    visible = [c for c in chars if not c.struck]
    printable = [c for c in chars if c.text.strip()]
    if not visible or not printable or not printable[0].struck:
        return visible

    first_word_index = next(
        (index for index, char in enumerate(visible) if char.text.isalnum()),
        None,
    )
    return visible[first_word_index:] if first_word_index is not None else []


def _line_has_strike(chars: list[Char]) -> bool:
    printable = [c for c in chars if c.text.strip()]
    if not printable:
        return False
    visible = "".join(c.text for c in chars if not c.struck).strip()
    if not visible:
        return True
    visible_alnum = [ch for ch in visible if ch.isalnum()]
    if not visible_alnum:
        return True
    if sum(c.struck for c in printable) / len(printable) > 0.85 and len(visible_alnum) <= 2:
        return True
    first_visible = next((ch for ch in visible if not ch.isspace()), "")
    return bool(printable[0].struck and first_visible.isalnum())


def _lines(chars: list[Char]) -> list[tuple[tuple[int, int], list[Char]]]:
    by_line: dict[tuple[int, int], list[Char]] = {}
    for char in chars:
        by_line.setdefault((char.page, round(char.y_mid)), []).append(char)
    return [(key, sorted(value, key=lambda c: c.x0)) for key, value in sorted(by_line.items())]


def _within_clause_range(char: Char, anchor: _Anchor, end_page: int, end_y: float) -> bool:
    if char.page == anchor.page and char.y_mid <= anchor.y + _TITLE_LINE_TOLERANCE:
        return False  # skip the anchor's own line (carries title, not body)
    return not (char.page == end_page and char.y_mid >= end_y - _TITLE_LINE_TOLERANCE)
