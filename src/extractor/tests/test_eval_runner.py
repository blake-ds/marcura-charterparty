"""Eval runner self-tests — invoke against the sample PDF, expect all green."""

from __future__ import annotations

from pathlib import Path

import pytest
from extractor.eval import run_eval

PDF = Path(__file__).resolve().parents[3] / "voyage-charter-example.pdf"


@pytest.fixture(scope="session")
def report():
    if not PDF.exists():
        pytest.skip(f"Sample PDF missing: {PDF}")
    return run_eval(PDF)


def test_all_eval_checks_pass(report) -> None:
    assert report.all_ok, report.to_text()


def test_at_least_thirteen_checks_run(report) -> None:
    """Adding a check is fine; silently dropping one is not."""
    assert (len(report.passed) + len(report.failed)) >= 13


def test_report_text_contains_per_check_lines(report) -> None:
    text = report.to_text()
    assert "PASS  total clause count" in text
    assert "PASS  shellvoy first clause" in text
