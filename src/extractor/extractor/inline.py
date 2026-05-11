"""Parser for the Shell Additional and Essar Rider sections (inline layout).

Unlike SHELLVOY there is no left-margin title column. Each clause begins with
``N.`` flush against the left edge (x ≈ 50pt) followed by the title on the
same line; the body starts on the following line.

Three real-world wrinkles in this corpus:

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
from extractor.pdf import Char, Page, Word, line_vote_filter
from extractor.text import chars_to_text

_NUMBER_RE = re.compile(r"^(\d{1,3})\.?$")
_DOT_PREFIX_RE = re.compile(r"^\.(\S.*)?$")

_CLAUSE_NUMBER_X_MIN = 40.0
_CLAUSE_NUMBER_X_MAX = 110.0
_BODY_X_MIN = 30.0
_BODY_X_MAX = 580.0
_TITLE_LINE_TOLERANCE = 5.0  # glyphs within this many points of the anchor are part of the title

# Thresholds for :func:`_is_wholly_replaced` — the "Canada Clause / Sidi Kerir
# / Rotterdam" pattern where only the bare ``N.`` is visible on the anchor row
# and the body region is dominated by heavy-struck lines.
_ANCHOR_ROW_Y_TOLERANCE = 5.0  # glyphs within this many pts of the anchor row
_ANCHOR_TITLE_X_MIN = 75.0  # glyphs past this x are title content (numbers live at x ≈ 50-65)
_ANCHOR_MIN_PRINTABLE = 3  # too few glyphs on the anchor row to judge title-struck reliably
_ANCHOR_STRUCK_RATIO = 0.6  # anchor row must be at least this struck to be "title struck"
_BODY_LINE_HEAVY_RATIO = 0.75  # per-line struck ratio that marks the line "heavy"
_BODY_MIN_NONEMPTY_LINES = 2  # single-line bodies fall through to single-line clause logic
_BODY_HEAVY_FRACTION = 0.5  # body region's fraction of heavy lines that triggers the drop


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


def _is_wholly_replaced(
    pages: tuple[Page, ...],
    anchor: _Anchor,
    end_page: int,
    end_y: float,
) -> bool:
    """Drop a clause when its anchor row's title was struck *and* the body region
    is dominated by heavy-struck lines.

    Catches the "Canada Clause / Sidi Kerir Clause / Rotterdam Port Dues
    Clause" pattern: only the bare ``N.`` is visible on the anchor row (title
    struck out), most lines below the anchor are entirely under strike rects,
    and the surviving mid-line glyphs are not real content but rather PDF
    artefacts where a strike rectangle ended short of the line width.
    """
    anchor_page = next(p for p in pages if p.number == anchor.page)
    anchor_row_printable = [
        c
        for c in anchor_page.chars
        if abs(c.y_mid - anchor.y) <= _ANCHOR_ROW_Y_TOLERANCE
        and c.x0 > _ANCHOR_TITLE_X_MIN
        and c.text.strip()
    ]
    if len(anchor_row_printable) < _ANCHOR_MIN_PRINTABLE:
        return False
    struck = sum(1 for c in anchor_row_printable if c.struck)
    if struck / len(anchor_row_printable) < _ANCHOR_STRUCK_RATIO:
        return False

    body_lines: dict[tuple[int, int], list[Char]] = {}
    for page in pages:
        if page.number < anchor.page or page.number > end_page:
            continue
        for char in page.chars:
            if not (_BODY_X_MIN < char.x_mid < _BODY_X_MAX):
                continue
            if char.page == anchor.page and char.y_mid <= anchor.y + _TITLE_LINE_TOLERANCE:
                continue
            if char.page == end_page and char.y_mid >= end_y - _TITLE_LINE_TOLERANCE:
                continue
            body_lines.setdefault((char.page, round(char.y_mid)), []).append(char)

    nonempty = 0
    heavy = 0
    for chars in body_lines.values():
        printable = [c for c in chars if c.text.strip()]
        if not printable:
            continue
        nonempty += 1
        if sum(1 for c in printable if c.struck) / len(printable) >= _BODY_LINE_HEAVY_RATIO:
            heavy += 1
    if nonempty < _BODY_MIN_NONEMPTY_LINES:
        return False  # single-line or empty region — leave to downstream logic
    return heavy / nonempty >= _BODY_HEAVY_FRACTION


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

    if _is_wholly_replaced(pages, anchor, end_page, end_y):
        return None

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
    """All body glyphs (struck + visible) in the clause's y-range; line+word filtered.

    Uses the same :func:`pdf.line_vote_filter` as the SHELLVOY parser: whole-line
    vote (line dropped only when left-most printable glyph is struck *and* the
    line is >``_LINE_VOTE_STRIKE_RATIO`` struck) plus word-level promotion (any
    struck glyph in a word → drop the whole word). The previous bespoke inline
    filter was correct on indemnity-style fragments but over-aggressive on lines
    whose
    *first printable char* was struck — it dropped lines like
    ``[STRUCK B.Flush] pumps and lines including decks lines, manifolds, drop
    lines and any other lines connected`` where the visible content is a real
    new word after a whitespace gap. The unified word-level filter keeps the
    visible content of those lines and still throws away mid-word fragments.
    """
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
    return line_vote_filter(candidates)


def _within_clause_range(char: Char, anchor: _Anchor, end_page: int, end_y: float) -> bool:
    if char.page == anchor.page and char.y_mid <= anchor.y + _TITLE_LINE_TOLERANCE:
        return False  # skip the anchor's own line (carries title, not body)
    return not (char.page == end_page and char.y_mid >= end_y - _TITLE_LINE_TOLERANCE)
