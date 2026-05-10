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
from extractor.pdf import Char, Page, Word, line_vote_filter
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


_SENTENCE_OPENER_RE = re.compile(r'^[A-Z0-9("“‘]')
_MEANINGFUL_TITLE_RE = re.compile(r"[A-Za-z]{2,}")


def _build_clause(
    pages: tuple[Page, ...],
    anchor: _Anchor,
    next_anchor: _Anchor | None,
    section: Section,
) -> Clause | None:
    """Materialize a clause, classifying the anchor's inline content.

    Three cases differ by the *shape* of the anchor's title and whether body
    text exists below it:

    * **Heading + body** — ``anchor.title`` looks like a clause heading
      (short, no mid-string period) and body lines follow. Standard case.
    * **Single-line clause** — the inline anchor content *is* the clause
      (essar-16 "All voyage instructions … by telex/Fax/E mail only."). We
      promote it into ``text`` and leave ``title`` empty.
    * **Sentence continuation** — the anchor line and body lines together
      form one wrapped sentence (essar-21). The title text contains a
      mid-string period; we concatenate it with the body and drop the
      separate-title slot.

    Body text that begins with a lowercase letter is treated as residue from
    a fully-struck clause and discarded — it is, in legal-document terms,
    not a clause but the tail end of one that was crossed out.
    """
    end_page = pages[-1].number if next_anchor is None else next_anchor.page
    end_y = float("inf") if next_anchor is None else next_anchor.y

    body_chars = list(_collect_body_chars(pages, anchor, end_page, end_y))
    body_text = chars_to_text(body_chars)
    if body_text and not _SENTENCE_OPENER_RE.match(body_text):
        body_text = ""  # mid-word fragment leaked from struck text

    title = anchor.title if _MEANINGFUL_TITLE_RE.search(anchor.title) else ""
    page_end = max(anchor.page, end_page) if body_text else anchor.page

    if not body_text:
        if not title:
            return None
        return Clause(
            section=section,
            ordinal=anchor.ordinal,
            title="",
            text=title,
            page_start=anchor.page,
            page_end=anchor.page,
        )

    if title and "." in title.rstrip("."):
        # Mid-string period — the "title" is the first sentence of the body.
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


def _collect_body_chars(
    pages: tuple[Page, ...], anchor: _Anchor, end_page: int, end_y: float
) -> list[Char]:
    """All body glyphs (struck + visible) in the clause's y-range; line-vote filtered."""
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
