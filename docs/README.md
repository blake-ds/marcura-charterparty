# Documentation

Submission docs for the Marcura *Charter Party Document Parser* challenge. See `docs/task.md` for the verbatim assignment.

## How these docs work

Two formats, one truth — the [r/ClaudeAI consensus on AI-coded docs](https://www.reddit.com/r/ClaudeAI/comments/1t8aecu/the_unreasonable_effectiveness_of_html_when_using/):

- **Markdown source-of-truth.** `.md` in this folder is canonical: lightweight, diff-friendly, parsed cleanly by any LLM agent (Claude Code, Codex, Cursor, Antigravity) and rendered well by GitHub.
- **HTML showcase.** `docs/site/index.html` is a single self-contained, hand-crafted snapshot — open it directly in a browser, no build system. Designed for the human reviewer.

Inline HTML inside `.md` is used only where markdown lacks expression: `<details>` for collapsible deep dives, `<dl>` for the glossary, `<figure>` for diagrams.

## Index

| Page | What it covers |
|------|----------------|
| [`task.md`](task.md) | The original Marcura assignment, preserved verbatim. |
| [`architecture.md`](architecture.md) | How the parser is designed — pipeline, section handling, LLM role. |
| [`glossary.md`](glossary.md) | Maritime + technical terms a non-shipping reader will hit. |
| [`development.md`](development.md) | Setup, env, commands, testing, pre-commit. |
