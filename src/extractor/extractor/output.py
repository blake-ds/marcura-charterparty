"""Serialize extracted clauses to the deliverable artefacts.

Two outputs share the same payload:

- ``output/clauses.json`` — the README-mandated wire format ``[{id, title, text}]``.
- ``output/clauses.html`` — a hand-styled, self-contained browseable view of
  the same data, rendered without a framework so that it survives any
  environment that can open an HTML file.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from extractor.models import Clause


def write_json(clauses: list[Clause], path: Path) -> None:
    """Write the spec-compliant JSON file."""
    payload = [c.to_spec_dict() for c in clauses]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_html(clauses: list[Clause], path: Path) -> None:
    """Render a self-contained, navigable HTML view of the clauses."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_html(clauses), encoding="utf-8")


def _render_html(clauses: list[Clause]) -> str:
    by_section: dict[str, list[Clause]] = {}
    for clause in clauses:
        by_section.setdefault(clause.section.value, []).append(clause)

    section_titles = {
        "shellvoy": "SHELLVOY 5 — standard clauses",
        "additional": "Shell Additional Clauses (Feb 1999)",
        "essar": "Essar Rider Clauses (Dec 2006)",
    }

    section_blocks: list[str] = []
    toc_blocks: list[str] = []
    for section_key in ("shellvoy", "additional", "essar"):
        items = by_section.get(section_key, [])
        if not items:
            continue
        toc_blocks.append(
            f'<li><a href="#{section_key}">{html.escape(section_titles[section_key])} '
            f'<span class="count">({len(items)})</span></a></li>'
        )
        clause_html = "\n".join(_render_clause(c) for c in items)
        section_blocks.append(
            f'<section id="{section_key}">\n'
            f"  <h2>{html.escape(section_titles[section_key])} "
            f'<span class="count">{len(items)} clauses</span></h2>\n'
            f"  {clause_html}\n"
            f"</section>"
        )

    toc = "\n".join(toc_blocks)
    body = "\n".join(section_blocks)
    total = len(clauses)
    return _PAGE_TEMPLATE.format(toc=toc, body=body, total=total)


def _render_clause(clause: Clause) -> str:
    paragraphs = [p.strip() for p in clause.text.split("\n\n") if p.strip()]
    body = "\n  ".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)
    body_html = f"  {body}\n" if body else ""
    return (
        f'<article id="{html.escape(clause.id)}">\n'
        f'  <header><span class="id">{html.escape(clause.id)}</span>'
        f"<h3>{html.escape(clause.title) or '<em>(untitled)</em>'}</h3></header>\n"
        f"{body_html}"
        f"</article>"
    )


_PAGE_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Charter party clauses — extracted</title>
<style>
:root {{
  --ink: #1a1a1a;
  --ink-soft: #555;
  --paper: #fafaf7;
  --rule: #e6e1d6;
  --accent: #2d5b8e;
  --code: #f3efe3;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font: 16px/1.65 "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  background: var(--paper);
  color: var(--ink);
}}
.wrap {{
  max-width: 880px;
  margin: 0 auto;
  padding: 64px 32px 96px;
}}
header.page {{
  border-bottom: 1px solid var(--rule);
  padding-bottom: 24px;
  margin-bottom: 32px;
}}
header.page h1 {{
  margin: 0 0 8px;
  font-size: 36px;
  letter-spacing: -0.01em;
}}
header.page p {{
  margin: 0;
  color: var(--ink-soft);
  font-size: 15px;
}}
nav.toc {{
  background: white;
  border: 1px solid var(--rule);
  padding: 20px 28px;
  margin-bottom: 48px;
  border-radius: 6px;
}}
nav.toc h2 {{
  margin: 0 0 12px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
  font-weight: 600;
}}
nav.toc ol {{
  margin: 0;
  padding-left: 24px;
}}
nav.toc li {{ margin: 4px 0; }}
nav.toc a {{
  color: var(--accent);
  text-decoration: none;
}}
nav.toc a:hover {{ text-decoration: underline; }}
.count {{
  color: var(--ink-soft);
  font-weight: normal;
  font-size: 0.85em;
}}
section {{
  margin-bottom: 64px;
}}
section h2 {{
  font-size: 22px;
  margin: 0 0 24px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent);
}}
article {{
  margin-bottom: 36px;
  padding-top: 8px;
}}
article header {{
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}}
article header h3 {{
  margin: 0;
  font-size: 19px;
  font-weight: 600;
}}
.id {{
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  background: var(--code);
  padding: 2px 8px;
  border-radius: 4px;
  color: var(--ink-soft);
}}
article p {{
  margin: 0 0 12px;
  text-align: justify;
  hyphens: auto;
}}
footer.page {{
  border-top: 1px solid var(--rule);
  padding-top: 24px;
  margin-top: 48px;
  font-size: 14px;
  color: var(--ink-soft);
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --ink: #e8e6df;
    --ink-soft: #a09b8e;
    --paper: #1a1a1a;
    --rule: #2c2926;
    --accent: #6ba3e0;
    --code: #2c2926;
  }}
  nav.toc {{ background: #232220; }}
}}
</style>
</head>
<body>
<div class="wrap">
  <header class="page">
    <h1>Charter party clauses</h1>
    <p>{total} clauses extracted from <code>voyage-charter-example.pdf</code>
       — strike-through filtered.</p>
  </header>
  <nav class="toc" aria-label="Sections">
    <h2>Sections</h2>
    <ol>
      {toc}
    </ol>
  </nav>
  {body}
  <footer class="page">
    Open the markdown source-of-truth in <code>docs/</code> for the architecture write-up.
    The deliverable wire-format JSON is at <code>output/clauses.json</code>.
  </footer>
</div>
</body>
</html>
"""
