# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## 1.0.0 — 2026-07-06

First public release, published to PyPI as
[`overleaf-latex-mcp`](https://pypi.org/project/overleaf-latex-mcp/).

### Highlights

- **MCP server for Overleaf + LaTeX.** Plug it into Claude Code, GitHub Copilot,
  Google Antigravity, or any MCP stdio client and let the agent read, draft,
  lint, format, fix, compile, and sync your LaTeX project.
- **Free-tier Overleaf sync.** Native `olsync_pull` / `olsync_push` work without
  Overleaf Premium, so an agent can do `pull → edit → push` in one turn. Premium
  git sync and a manual ZIP round-trip are also supported.
- **24 MCP tools**, including 7 pure-Python static checks (math brackets,
  align-column drift, figure completeness, table column match, package conflicts,
  heading-case consistency, dangling refs / unused labels / uncited entries).
- **Graceful degradation.** `latexindent`, `chktex`, and `latexmk` are optional;
  missing binaries are reported via `detect_capabilities` and the server always
  starts.
- **Log translation.** `explain_log` turns cryptic LaTeX compile output into
  structured errors with one-line fixes.

### Install

```bash
uvx overleaf-latex-mcp            # run without installing
uv tool install overleaf-latex-mcp
pipx install overleaf-latex-mcp
```

### Notes

- The PyPI distribution is named `overleaf-latex-mcp` (the name `overleaf-mcp` is
  held by an unrelated project); the import package remains `overleaf_mcp`.
- Requires Python 3.11+.
