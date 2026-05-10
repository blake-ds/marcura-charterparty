"""Parser for the SHELLVOY 5 boilerplate (two-column layout).

SHELLVOY pages put the clause **title in a narrow left column** (x ≈ 42–100)
and the **clause body in a wide right column** (x ≈ 110–510), with a thin
gutter beyond ~520pt holding the printed source-line numbers (``67``, ``68``,
…). Each clause begins with an N. token at the left edge of the body column.

A subtlety: when a clause has been struck out and replaced (e.g. clause 2
*Cleanliness of tanks*), the printed title sits next to the **original**
struck-out body, while the *visible* clause-number anchor sits below the
replacement text. Worse, when an entire neighbouring clause was struck out
(e.g. clause 21 *Over age insurance*) its title still sits in the left
margin — close enough to the next visible clause's title to be merged with
it under any naive gap-based grouping.

The two-pass title attachment below handles both cases:

1. **Greedy pass.** Each anchor claims same-row plus immediately-below
   left-margin lines (gap < ``_MULTILINE_TITLE_GAP``). This handles the
   common case where the title wraps onto a couple of lines starting at the
   anchor's row.
2. **Orphan pass.** Any unclaimed left-margin block is offered to the next
   anchor below — but only if that anchor still has no title. That covers
   the *replacement-clause* case (title above the visible anchor) without
   stealing titles from wholly-struck clauses (whose neighbours already have
   their own title).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from extractor.models import Clause, Section
from extractor.pdf import Char, Page, Word
from extractor.text import chars_to_text

_CLAUSE_NUMBER_RE = re.compile(r"^(\d{1,2})\.$")

_TITLE_COLUMN_MAX_X = 105.0
_BODY_COLUMN_MIN_X = 105.0
# Body glyphs run up to ≈510pt; the line-number gutter starts at ≈525pt. We
# split between them so border-case glyphs ('h' at 502pt of "the") are kept
# while two-digit line numbers ('67', '68', …) are cleanly excluded.
_BODY_COLUMN_MAX_X = 520.0

_CLAUSE_NUMBER_X_MIN = 115.0
_CLAUSE_NUMBER_X_MAX = 145.0

# Within-title intra-line gaps are ≈10–12pt; anything bigger is a title boundary.
_MULTILINE_TITLE_GAP = 14.0
# An above-anchor orphan block is a candidate title only if it ends within this
# many points of the anchor row. Bigger gaps are pages of struck body.
_ORPHAN_LOOKBACK_MAX = 100.0


class _Anchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    ordinal: int
    page: int
    y: float
    word: Word


class _LeftMarginLine(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    y: float
    text: str


def parse(pages: tuple[Page, ...]) -> list[Clause]:
    """Parse the SHELLVOY pages into a list of clauses."""
    anchors = _find_anchors(pages)
    titles = _attach_titles(pages, anchors)

    clauses: list[Clause] = []
    for index, anchor in enumerate(anchors):
        next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
        clause = _build_clause(pages, anchor, next_anchor, titles[index])
        if clause is not None:
            clauses.append(clause)
    return clauses


def _find_anchors(pages: tuple[Page, ...]) -> list[_Anchor]:
    anchors: list[_Anchor] = []
    for page in pages:
        for word in page.visible_words():
            match = _CLAUSE_NUMBER_RE.match(word.text)
            if match is None:
                continue
            if not (_CLAUSE_NUMBER_X_MIN <= word.x0 <= _CLAUSE_NUMBER_X_MAX):
                continue
            anchors.append(
                _Anchor(
                    ordinal=int(match.group(1)),
                    page=word.page,
                    y=word.y_mid,
                    word=word,
                )
            )
    return sorted(anchors, key=lambda a: (a.page, a.y))


def _left_margin_lines(page: Page) -> list[_LeftMarginLine]:
    """Group left-margin glyphs into ``(y, line_text)`` tuples sorted by y."""
    by_y: dict[int, list[Char]] = {}
    for char in page.visible_chars():
        if char.x_mid >= _TITLE_COLUMN_MAX_X:
            continue
        by_y.setdefault(round(char.y_mid), []).append(char)
    out: list[_LeftMarginLine] = []
    for y in sorted(by_y):
        chars = sorted(by_y[y], key=lambda c: c.x0)
        text = "".join(c.text for c in chars).strip()
        if text:
            out.append(_LeftMarginLine(page=page.number, y=float(y), text=text))
    return out


def _attach_titles(pages: tuple[Page, ...], anchors: list[_Anchor]) -> list[str]:
    """Two-pass: greedy own-row + below-row, then orphan block fall-through."""
    titles: list[str] = ["" for _ in anchors]
    if not anchors:
        return titles

    by_page_anchors: dict[int, list[tuple[int, _Anchor]]] = {}
    for index, anchor in enumerate(anchors):
        by_page_anchors.setdefault(anchor.page, []).append((index, anchor))

    for page in pages:
        page_anchors = by_page_anchors.get(page.number, [])
        if not page_anchors:
            continue
        page_lines = _left_margin_lines(page)
        claimed = _greedy_claim(page_anchors, page_lines, titles)
        _orphan_attach(page_anchors, page_lines, claimed, titles)
    return titles


def _greedy_claim(
    page_anchors: list[tuple[int, _Anchor]],
    page_lines: list[_LeftMarginLine],
    titles: list[str],
) -> set[int]:
    """Each anchor claims same-row + below-row tightly-packed lines."""
    claimed: set[int] = set()
    for index, anchor in page_anchors:
        owned: list[int] = []
        last_y: float | None = None
        for line_idx, line in enumerate(page_lines):
            if line_idx in claimed:
                continue
            if line.y < anchor.y - 3:
                continue
            # If the line is the first one we'd claim, the gap is measured from
            # the anchor row itself — that allows same-row inline titles
            # (line.y == anchor.y) and rejects orphan blocks that float far
            # below the anchor with no inline title at all.
            baseline = last_y if last_y is not None else anchor.y
            if line.y - baseline > _MULTILINE_TITLE_GAP:
                break
            owned.append(line_idx)
            last_y = line.y
        if owned:
            titles[index] = " ".join(page_lines[i].text for i in owned)
            claimed.update(owned)
    return claimed


def _orphan_attach(
    page_anchors: list[tuple[int, _Anchor]],
    page_lines: list[_LeftMarginLine],
    claimed: set[int],
    titles: list[str],
) -> None:
    """Offer every still-unclaimed contiguous block to the next title-less anchor."""
    blocks: list[list[int]] = []
    current: list[int] = []
    last_y: float | None = None
    for line_idx, line in enumerate(page_lines):
        if line_idx in claimed:
            if current:
                blocks.append(current)
                current = []
            last_y = None
            continue
        if last_y is not None and (line.y - last_y) > _MULTILINE_TITLE_GAP:
            blocks.append(current)
            current = []
        current.append(line_idx)
        last_y = line.y
    if current:
        blocks.append(current)

    for block in blocks:
        block_y_end = page_lines[block[-1]].y
        # Find the next title-less anchor whose anchor.y is below the block end.
        candidate = next(
            (
                (idx, anchor)
                for idx, anchor in page_anchors
                if anchor.y > block_y_end and not titles[idx]
            ),
            None,
        )
        if candidate is None:
            continue
        idx, anchor = candidate
        if anchor.y - block_y_end > _ORPHAN_LOOKBACK_MAX:
            continue
        titles[idx] = " ".join(page_lines[i].text for i in block)


def _build_clause(
    pages: tuple[Page, ...],
    anchor: _Anchor,
    next_anchor: _Anchor | None,
    title: str,
) -> Clause | None:
    end_page = pages[-1].number if next_anchor is None else next_anchor.page
    end_y = float("inf") if next_anchor is None else next_anchor.y

    body_chars = list(_collect_body_chars(pages, anchor, end_page, end_y))
    text = chars_to_text(body_chars)
    if not text:
        return None

    return Clause(
        section=Section.SHELLVOY,
        ordinal=anchor.ordinal,
        title=title,
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
            if not (_BODY_COLUMN_MIN_X < char.x_mid < _BODY_COLUMN_MAX_X):
                continue
            if not _within_clause_range(char, anchor, end_page, end_y):
                continue
            if _is_clause_number_glyph(char, anchor.word):
                continue
            chars.append(char)
    return chars


def _within_clause_range(char: Char, anchor: _Anchor, end_page: int, end_y: float) -> bool:
    if char.page == anchor.page and char.y_mid < anchor.y - 2.0:
        return False
    return not (char.page == end_page and char.y_mid >= end_y - 2.0)


def _is_clause_number_glyph(char: Char, anchor_word: Word) -> bool:
    return (
        char.page == anchor_word.page
        and anchor_word.x0 - 0.5 <= char.x0 <= anchor_word.x1 + 0.5
        and abs(char.y_mid - anchor_word.y_mid) <= 2.5
    )
