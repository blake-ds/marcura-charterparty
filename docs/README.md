# Documentation

Submission docs for the Marcura *Charter Party Document Parser* challenge. See `docs/task.md` for the verbatim assignment.

## How these docs work

Two formats, one truth. The pattern is the one **Boris Cherny — the creator of Claude Code — uses himself**, as discussed in the [r/ClaudeAI thread on the unreasonable effectiveness of HTML for Claude-authored docs](https://www.reddit.com/r/ClaudeAI/comments/1t8aecu/the_unreasonable_effectiveness_of_html_when_using/):

> "HTML is vastly superior for human-readable outputs. Claude is weirdly good at it … Boris Cherny (the guy who invented Claude Code) does this himself to make plans easier to read."

So:

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
