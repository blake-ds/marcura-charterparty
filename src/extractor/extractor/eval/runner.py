"""Run the deterministic eval against the parser output.

Each check is a small, named, side-effect-free assertion. Results aggregate
into an :class:`EvalReport` that prints a short summary and exits non-zero on
any failure — exactly what CI needs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from importlib import resources
from pathlib import Path

from pydantic import BaseModel, Field

from extractor.models import Clause, Section
from extractor.pipeline import extract_clauses


class EvalReport(BaseModel):
    """Aggregate of every eval check that ran."""

    passed: list[str] = Field(default_factory=list)
    failed: list[tuple[str, str]] = Field(default_factory=list)

    def add(self, name: str, *, ok: bool, detail: str = "") -> None:
        if ok:
            self.passed.append(name)
        else:
            self.failed.append((name, detail))

    @property
    def all_ok(self) -> bool:
        return not self.failed

    def to_text(self) -> str:
        lines = [f"PASS  {name}" for name in self.passed]
        lines.extend(f"FAIL  {name}: {detail}" for name, detail in self.failed)
        lines.append("")
        lines.append(f"Total: {len(self.passed)} passed, {len(self.failed)} failed.")
        return "\n".join(lines)


def run_eval(pdf_path: Path, golden_path: Path | None = None) -> EvalReport:
    """Extract clauses, then check every assertion in the golden file."""
    golden = _load_golden(golden_path)
    clauses = extract_clauses(pdf_path)

    report = EvalReport()
    _check_total_count(clauses, golden, report)
    _check_section_counts(clauses, golden, report)
    _check_id_format(clauses, golden, report)
    _check_id_uniqueness(clauses, report)
    _check_section_ordering(clauses, report)
    _check_expected_ordinals(clauses, golden, report)
    _check_first_clause_per_section(clauses, golden, report)
    _check_specific_clauses(clauses, golden, report)
    _check_struck_absent(clauses, golden, report)
    _check_fragments_absent(clauses, golden, report)
    _check_kept_present(clauses, golden, report)
    _check_titles_non_silly(clauses, report)
    _check_no_embedded_anchor_leakage(clauses, golden, report)
    _check_text_starts_clean(clauses, report)
    return report


def _load_golden(path: Path | None) -> dict:
    if path is not None:
        return json.loads(path.read_text())
    return json.loads(resources.files("extractor.eval").joinpath("golden.json").read_text())


# --------------------------------------------------------------------- checks


def _check_total_count(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    expected = golden["expected_total"]
    actual = len(clauses)
    report.add(
        "total clause count",
        ok=actual == expected,
        detail=f"expected {expected}, got {actual}",
    )


def _check_section_counts(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    expected = golden["expected_counts"]
    actual = {s.value: 0 for s in Section}
    for clause in clauses:
        actual[clause.section.value] += 1
    for section, count in expected.items():
        report.add(
            f"{section} count",
            ok=actual[section] == count,
            detail=f"expected {count}, got {actual[section]}",
        )


def _check_id_format(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    pattern = re.compile(golden["id_format_regex"])
    bad = [c.id for c in clauses if not pattern.match(c.id)]
    report.add(
        "id format",
        ok=not bad,
        detail=f"{len(bad)} ids violate {golden['id_format_regex']!r}: {bad[:5]}",
    )


def _check_id_uniqueness(clauses: list[Clause], report: EvalReport) -> None:
    ids = [c.id for c in clauses]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    report.add(
        "ids unique",
        ok=not duplicates,
        detail=f"duplicate ids: {duplicates}",
    )


def _check_section_ordering(clauses: list[Clause], report: EvalReport) -> None:
    by_section: dict[Section, list[int]] = {s: [] for s in Section}
    for clause in clauses:
        by_section[clause.section].append(clause.ordinal)
    failures: list[str] = []
    for section, ordinals in by_section.items():
        if ordinals != sorted(ordinals):
            failures.append(f"{section.value}: {ordinals}")
    report.add(
        "ordinals monotonic per section",
        ok=not failures,
        detail="; ".join(failures),
    )


def _check_expected_ordinals(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    """Per-section ordinal lists must match exactly — catches drops + duplicates."""
    actual: dict[str, list[int]] = {s.value: [] for s in Section}
    for clause in clauses:
        actual[clause.section.value].append(clause.ordinal)
    for section, expected in golden["expected_ordinals_per_section"].items():
        report.add(
            f"{section} ordinals exact",
            ok=actual[section] == expected,
            detail=f"expected {expected}, got {actual[section]}",
        )


def _check_specific_clauses(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    """Frozen expectations on individual clauses — regression tripwires."""
    by_id = {c.id: c for c in clauses}
    for clause_id, expected in golden.get("specific_clauses", {}).items():
        clause = by_id.get(clause_id)
        if clause is None:
            report.add(f"{clause_id} present", ok=False, detail="missing from output")
            continue
        ok = clause.title == expected["title"] and clause.text.startswith(
            expected["text_starts_with"]
        )
        if "text_exact" in expected:
            ok = ok and clause.text == expected["text_exact"]
        detail = f"got title={clause.title!r}, text[:60]={clause.text[:60]!r}" if not ok else ""
        report.add(f"{clause_id} matches expected", ok=ok, detail=detail)


def _check_no_embedded_anchor_leakage(
    clauses: list[Clause], golden: dict, report: EvalReport
) -> None:
    """No clause text may contain a fragment of the *next* clause's anchor."""
    pattern = re.compile(golden["embedded_anchor_pattern_must_not_appear"])
    leaked = [c.id for c in clauses if pattern.search(c.text)]
    report.add(
        "no embedded anchor leakage",
        ok=not leaked,
        detail=f"clauses with leaked next-anchor fragments: {leaked}",
    )


def _check_first_clause_per_section(
    clauses: list[Clause], golden: dict, report: EvalReport
) -> None:
    by_section: dict[str, list[Clause]] = {}
    for clause in clauses:
        by_section.setdefault(clause.section.value, []).append(clause)
    for section_key, expected in golden["first_clause_per_section"].items():
        items = by_section.get(section_key, [])
        if not items:
            report.add(f"{section_key} first clause", ok=False, detail="no clauses extracted")
            continue
        first = items[0]
        ok = first.id == expected["id"] and first.title == expected["title"]
        ok = ok and first.text.startswith(expected["text_starts_with"])
        if "text_ends_with" in expected:
            ok = ok and first.text.endswith(expected["text_ends_with"])
        detail = (
            f"got id={first.id!r} title={first.title!r} text[:60]={first.text[:60]!r}"
            if not ok
            else ""
        )
        report.add(f"{section_key} first clause", ok=ok, detail=detail)


def _check_struck_absent(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    _check_snippets_absent(
        clauses,
        snippets=golden["struck_must_be_absent"],
        name="struck snippets absent",
        detail_label="leaked snippets",
        report=report,
    )


def _check_fragments_absent(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    _check_snippets_absent(
        clauses,
        snippets=golden["fragment_must_be_absent"],
        name="strike fragments absent",
        detail_label="leaked fragments",
        report=report,
    )


def _check_snippets_absent(
    clauses: list[Clause],
    *,
    snippets: list[str],
    name: str,
    detail_label: str,
    report: EvalReport,
) -> None:
    all_text = " ".join(c.text for c in clauses)
    leaked = [snippet for snippet in snippets if snippet in all_text]
    report.add(
        name,
        ok=not leaked,
        detail=f"{detail_label}: {leaked}",
    )


def _check_kept_present(clauses: list[Clause], golden: dict, report: EvalReport) -> None:
    all_text = " ".join((c.text + " " + c.title) for c in clauses)
    missing = [snippet for snippet in golden["kept_must_be_present"] if snippet not in all_text]
    report.add(
        "kept snippets present",
        ok=not missing,
        detail=f"missing snippets: {missing}",
    )


def _check_text_starts_clean(clauses: list[Clause], report: EvalReport) -> None:
    """A clause's text must start with a plausible sentence opener.

    Mid-word fragments left over from partial strike rectangles look like
    text that begins with a lowercase letter. Real clauses begin with
    upper-case words, parenthesised sub-points, digits, or quotes.
    """
    pattern = re.compile(r'^[A-Z0-9("“‘]')
    bad = [c.id for c in clauses if c.text and not pattern.match(c.text)]
    report.add(
        "text starts with sentence opener",
        ok=not bad,
        detail=f"clauses starting with a non-opener char: {bad}",
    )


def _check_titles_non_silly(clauses: list[Clause], report: EvalReport) -> None:
    """Trivial structural check on titles — no leaked headers / line-numbers."""
    suspicious = [
        c.id
        for c in clauses
        if any(needle in c.title for needle in ("Issued July", "SHELLVOY", "PART II"))
    ]
    report.add(
        "no header-text in titles",
        ok=not suspicious,
        detail=f"suspicious titles in: {suspicious}",
    )


# --------------------------------------------------------------------- CLI


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="extractor.eval", description=__doc__)
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("voyage-charter-example.pdf"),
        help="Charter party PDF to extract from.",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Override path to golden.json (defaults to packaged file).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2

    report = run_eval(args.pdf, args.golden)
    print(report.to_text())
    return 0 if report.all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
