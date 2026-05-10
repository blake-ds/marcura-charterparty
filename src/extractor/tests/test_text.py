from extractor.pdf import Char
from extractor.text import chars_to_text


def _char(text: str, x: float, y: float, *, page: int = 1, struck: bool = False) -> Char:
    return Char(text=text, x0=x, y0=y, x1=x + 5, y1=y + 10, page=page, struck=struck)


def test_chars_to_text_groups_by_line() -> None:
    chars = [
        _char("H", 0, 0),
        _char("i", 5, 0),
        _char("y", 0, 12),  # next line
        _char("o", 5, 12),
    ]
    assert chars_to_text(chars) == "Hi yo"


def test_chars_to_text_inserts_paragraph_break_for_large_gap() -> None:
    chars = [
        _char("A", 0, 0),
        _char("B", 0, 12),  # one line down (~12pt)
        _char("C", 0, 60),  # ≈4 line-heights gap → paragraph break
    ]
    out = chars_to_text(chars)
    assert "\n\n" in out
    assert out.startswith("A B")
    assert out.endswith("C")


def test_chars_to_text_separates_pages_even_at_same_y() -> None:
    chars = [
        _char("A", 0, 100, page=1),
        _char("B", 0, 100, page=2),
    ]
    assert chars_to_text(chars) == "A\n\nB"


def test_chars_to_text_handles_empty() -> None:
    assert chars_to_text([]) == ""
