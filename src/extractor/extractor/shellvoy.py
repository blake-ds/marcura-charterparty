"""Parser for the SHELLVOY 5 boilerplate (two-column layout).

SHELLVOY pages put the clause **title in a narrow left column** (x ≈ 42–100)
and the **clause body in a wide right column** (x ≈ 110–510), with a thin
gutter beyond ~520pt holding the printed source-line numbers (``67``, ``68``,
…). Each clause begins with an N. token at the left edge of the body column.

A subtlety: when a clause has been struck out and replaced (e.g. clause 2
*Cleanliness of tanks*), the printed title sits next to the **original**
struck-out body, while the *visible* clause-number anchor sits below the
replacement text. We therefore find the title blocks first and bind each one
to the first clause anchor that begins at or below it.
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

_TITLE_BLOCK_GAP = 15.0  # vertical gap that separates one title block from the next


class _Anchor(BaseModel):
    model_config = ConfigDict(frozen=True)

    ordinal: int
    page: int
    y: float
    word: Word


class _TitleBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    page: int
    y_start: float
    y_end: float
    text: str


def parse(pages: tuple[Page, ...]) -> list[Clause]:
    """Parse the SHELLVOY pages into a list of clauses."""
    anchors = _find_anchors(pages)
    title_blocks = _find_title_blocks(pages)
    titles_by_anchor = _attach_titles(anchors, title_blocks)

    clauses: list[Clause] = []
    for index, anchor in enumerate(anchors):
        next_anchor = anchors[index + 1] if index + 1 < len(anchors) else None
        clause = _build_clause(pages, anchor, next_anchor, titles_by_anchor.get(id(anchor), ""))
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


def _find_title_blocks(pages: tuple[Page, ...]) -> list[_TitleBlock]:
    """Group left-margin visible glyphs into one block per clause title."""
    blocks: list[_TitleBlock] = []
    for page in pages:
        title_chars = [c for c in page.visible_chars() if c.x_mid < _TITLE_COLUMN_MAX_X]
        if not title_chars:
            continue
        for block_chars in _split_into_blocks(title_chars):
            text = chars_to_text(block_chars)
            if not text:
                continue
            ys = [c.y_mid for c in block_chars]
            blocks.append(_TitleBlock(page=page.number, y_start=min(ys), y_end=max(ys), text=text))
    return blocks


def _split_into_blocks(chars: list[Char]) -> list[list[Char]]:
    """Cluster ``chars`` into blocks by vertical proximity (page-local)."""
    by_y: dict[int, list[Char]] = {}
    for char in chars:
        by_y.setdefault(round(char.y_mid), []).append(char)

    sorted_lines = sorted(by_y.items())
    blocks: list[list[Char]] = []
    current: list[Char] = []
    last_y: float | None = None
    for y, line_chars in sorted_lines:
        if last_y is not None and (y - last_y) > _TITLE_BLOCK_GAP and current:
            blocks.append(current)
            current = []
        current.extend(line_chars)
        last_y = y
    if current:
        blocks.append(current)
    return blocks


def _attach_titles(anchors: list[_Anchor], title_blocks: list[_TitleBlock]) -> dict[int, str]:
    """Map each anchor (by ``id()``) to its title block — first anchor at/below."""
    titles: dict[int, str] = {}
    for block in title_blocks:
        owner = next(
            (a for a in anchors if a.page == block.page and a.y >= block.y_start - 0.5),
            None,
        )
        if owner is not None:
            titles[id(owner)] = block.text
    return titles


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
