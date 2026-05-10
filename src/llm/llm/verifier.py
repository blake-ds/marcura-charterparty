"""LLM verifier — judges the deterministic output, never authors text.

The verifier receives the extracted clauses as **HTML-tagged structured input**
(``<clause id=…><title>…</title><text>…</text></clause>``); LLMs handle
hierarchy in HTML markedly better than in flat concatenations. It returns a
list of :class:`Anomaly` records the caller may surface to the developer.

The verifier never mutates clause text — that would re-introduce hallucination
risk in a fidelity-critical legal pipeline. Anomalies are advisory only.
"""

from __future__ import annotations

import html
import json
import logging
from collections.abc import Callable

from extractor.models import Clause
from pydantic import BaseModel, ConfigDict

from llm.clients import ChatClient, build_chat_client
from llm.settings import LLMSettings

log = logging.getLogger(__name__)


class Anomaly(BaseModel):
    """An advisory finding from the verifier."""

    model_config = ConfigDict(frozen=True)

    clause_id: str
    issue: str


_SYSTEM_PROMPT = """\
You are a maritime contracts QA assistant. You are given clauses that were
extracted **deterministically** from a charter party PDF. Your job is to
inspect the structure for *anomalies only* — never rewrite, paraphrase, or
fill in text. Return strict JSON.

Look for:
1. Clauses whose title doesn't read like a charter party clause heading.
2. Text that begins or ends mid-sentence (likely truncation).
3. Two clauses that look merged into one (multiple distinct subjects in `text`).
4. Out-of-order ordinals within a section.
5. Bodies that look suspiciously short for a real clause
   (1–2 sentences may be fine; 1–2 words probably isn't).

Skip clauses that look fine. The deterministic extractor is already good — most
runs should yield zero or only a handful of anomalies.
"""

_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "anomalies": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "issue": {"type": "string"},
                },
                "required": ["id", "issue"],
            },
        }
    },
    "required": ["anomalies"],
}


def verify(
    clauses: list[Clause],
    *,
    settings: LLMSettings | None = None,
    client: ChatClient | None = None,
) -> list[Anomaly]:
    """Send ``clauses`` to the LLM and return any anomalies it flags."""
    settings = settings or LLMSettings()
    client = client or build_chat_client(settings.verifier_model, settings)
    payload = _render_html(clauses)
    raw = client.chat(
        deployment=settings.verifier_model,
        system=_SYSTEM_PROMPT,
        user=payload,
        json_schema=_RESPONSE_SCHEMA,
    )
    return _parse(raw)


def build_verifier(
    settings: LLMSettings | None = None,
) -> Callable[[list[Clause]], None]:
    """Build the side-effect-y verifier hook the CLI plugs into the pipeline.

    The returned callable runs :func:`verify` and logs any anomalies. It does
    not raise — a verifier outage must never break a deterministic extraction.
    """
    settings = settings or LLMSettings()

    def _hook(clauses: list[Clause]) -> None:
        try:
            anomalies = verify(clauses, settings=settings)
        except Exception:
            log.exception("Verifier call failed; treating as no anomalies.")
            return
        if not anomalies:
            log.info("Verifier: no anomalies detected on %d clauses.", len(clauses))
            return
        log.warning("Verifier flagged %d anomaly/anomalies:", len(anomalies))
        for a in anomalies:
            log.warning("  [%s] %s", a.clause_id, a.issue)

    return _hook


def _render_html(clauses: list[Clause]) -> str:
    parts = [f'<clauses count="{len(clauses)}">']
    for clause in clauses:
        parts.append(
            f'  <clause id="{html.escape(clause.id)}" '
            f'section="{html.escape(clause.section.value)}" '
            f'ordinal="{clause.ordinal}">'
        )
        parts.append(f"    <title>{html.escape(clause.title)}</title>")
        parts.append(f"    <text>{html.escape(clause.text)}</text>")
        parts.append("  </clause>")
    parts.append("</clauses>")
    return "\n".join(parts)


def _parse(raw: str) -> list[Anomaly]:
    payload = json.loads(raw)
    return [Anomaly(clause_id=item["id"], issue=item["issue"]) for item in payload["anomalies"]]
