# Overleaf LaTeX MCP — Design

**Date:** 2026-04-22
**Status:** Draft for review

## Problem

LaTeX work on Overleaf is painful to get right: indentation, equation alignment, table columns, figure placement, reference/citation consistency, cryptic compile errors, and package conflicts all slow authors down. AI coding assistants (Claude Code, GitHub Copilot, Google Antigravity, etc.) can help, but today they have no way to read, format, lint, or compile an Overleaf project.

## Goal

Ship an npm-installable MCP server that exposes Overleaf-aware and LaTeX-aware tools to any MCP-compatible AI client. The server must:

1. Work for **Overleaf free-tier** users (no Premium required).
2. Work for **Overleaf Premium** users via git sync.
3. Work on **local `.tex` files** with no Overleaf account at all.
4. Cover the full set of formatting pain points: structural formatting, math, tables, figures, references/citations, compile errors, style consistency, and package conflicts.
5. Degrade gracefully when optional tools (`latexindent`, `chktex`, `latexmk`) are not installed.

## Non-goals

- Building a new LaTeX formatter from scratch (wrap `latexindent`).
- Injecting UI into the Overleaf web editor (not possible without self-hosting).
- Supporting self-hosted Overleaf Community/Server Pro specifically.
- Providing a hosted service or OAuth flow (users bring their own git token).
- Real-time collaborative editing or cursor sharing.

## Architecture

### Runtime

Python 3.11+ MCP server using the official `mcp` Python SDK. Published to PyPI as `overleaf-mcp`. Invoked by MCP clients via `uvx overleaf-mcp` (or `pipx run overleaf-mcp`). Project uses `uv` for dependency management and `pytest` for tests. Tool input schemas defined with `pydantic` v2.

### Operating modes (auto-detected)

| Mode | Trigger | Behavior |
|---|---|---|
| **Local** | `OVERLEAF_GIT_URL` empty | Operates on `project_root`. No network calls. |
| **Overleaf-synced** | `OVERLEAF_GIT_URL` + `OVERLEAF_GIT_TOKEN` set | `git clone`/`pull`/`push` against Overleaf git remote. |
| **ZIP-bridge** | User invokes `import_overleaf_zip` / `export_overleaf_zip` explicitly | Manual round-trip for free-tier users. |

A single process can move between Local and ZIP-bridge at runtime. Overleaf-synced mode requires env vars at startup.

### Capability detection

At startup, probe for optional binaries and config:

- `latexindent --version` → enables formatting tools
- `chktex --version` → enables linting
- `latexmk -v` → enables local compile
- Overleaf git env vars → enables sync tools
- `.latexindent.yaml` / `chktexrc` in `project_root` → used if present; otherwise defaults shipped with MCP

Missing capabilities produce a startup log line (on stderr) with install hints (`brew install …`, `apt install …`, MikTeX link). The server still starts; each unavailable tool returns a `ToolResult` with `ok=False`, `error="not installed"`, and a `suggestion` pointing at install instructions.

### State model

The server is **stateless between tool calls**. Each call re-reads files and (if needed) re-detects project structure. This keeps concurrent calls safe and avoids stale caches.

### Project detection

On any tool call that needs project context:

1. Main file: `% !TeX root = …` directive → `\documentclass` scan of root `.tex` files → fallback to `main.tex`.
2. Bibliography: scan for `\bibliography{…}` / `\addbibresource{…}`.
3. Custom classes/styles: enumerate `.cls` / `.sty` in `project_root`.
4. Sections: parse `\section`/`\subsection`/... for navigation.

## Tool Surface

All tools return structured `{ ok, data?, error?, suggestion? }`. File paths are validated to stay inside `project_root`.

### File/project awareness

- `list_tex_files()` — `.tex`/`.bib`/`.cls`/`.sty` in project
- `read_tex_file(path)` — content with line numbers
- `write_tex_file(path, content)` — atomic write (tmp + rename)
- `get_project_structure()` — main file, sections, bib files, custom classes

### Formatting (wraps `latexindent`)

- `format_file(path, options?)` — apply `latexindent` using project config if present
- `format_snippet(code)` — format a string, return formatted string (no disk write)
- `check_formatting(path)` — dry-run, return unified diff without writing

### Linting & style (wraps `chktex` + custom)

- `lint_file(path)` — `chktex` warnings with line/col + human explanation
- `check_consistency(paths)` — cross-file: heading case, dash style (`-`/`--`/`---`), smart quotes, ref/cite key conventions
- `find_unused_labels_and_refs()` — unused `\label`, dangling `\ref`/`\eqref`/`\cite`, orphan bib entries

### Math

- `check_math(path)` — unpaired `\left`/`\right`, mismatched `{`/`[`/`(` inside math, `&` column-count drift in `align`/`array`/`matrix`/`pmatrix`

### Tables

- `check_table(path, line)` — column-count vs column-spec, `\hline` placement, overfull hbox risk estimate
- `suggest_table_fix(path, line)` — proposed rewrite for the agent to review

### Figures

- `check_figures(path)` — every `figure` env has `\caption` + `\label`, `\includegraphics` width sanity, `\centering` present, float placement spec present

### Packages & classes

- `check_packages(path)` — duplicate `\usepackage`, known-bad combos (`subfig` + `subcaption`, wrong `hyperref` order), missing-but-used commands (e.g., `\SI{}` without `siunitx`)

### Compile & error translation (only if `latexmk` or Overleaf sync available)

- `compile(path)` — local `latexmk` OR Overleaf compile API (synced mode)
- `explain_log(logText)` — parse log into structured errors with suggested fixes

### Overleaf sync (synced mode only)

- `pull_from_overleaf()` — `git pull --rebase`
- `push_to_overleaf(message)` — stage all, commit, push
- `overleaf_status()` — branch, uncommitted changes, ahead/behind counts

### ZIP bridge (free-tier)

- `import_overleaf_zip(zipPath)` — unpack into `project_root`
- `export_overleaf_zip(outPath)` — zip current `project_root` for re-upload

## Configuration

```json
{
  "mcpServers": {
    "overleaf": {
      "command": "uvx",
      "args": ["overleaf-mcp"],
      "env": {
        "OVERLEAF_PROJECT_ROOT": "/absolute/path/to/project",
        "OVERLEAF_GIT_URL": "",
        "OVERLEAF_GIT_TOKEN": ""
      }
    }
  }
}
```

Alternative invocation: `"command": "pipx", "args": ["run", "overleaf-mcp"]` for users without `uv`.

`OVERLEAF_PROJECT_ROOT` is required. The other two are optional; supplying them enables synced mode.

## Sync behavior

- First `pull_from_overleaf` in an empty `project_root` does `git clone`. Subsequent calls do `git pull --rebase`.
- `push_to_overleaf(message)` stages all tracked changes (not new untracked files unless the agent explicitly adds them via `write_tex_file`), commits, and pushes.
- Merge conflicts are NOT auto-resolved. The tool returns the list of conflicting files and stops — the agent and user resolve via `write_tex_file`.
- Git credentials are injected via `GIT_ASKPASS` wrapper, never embedded in URLs or logged.

## Error handling

- Every tool returns a `ToolResult` pydantic model with fields `ok: bool`, `data: Any | None`, `error: str | None`, `suggestion: str | None`.
- Missing binary → `ok=False`, `error="latexindent not installed"`, `suggestion="brew install latexindent"` (platform-specific).
- Out-of-root path → returned as a failure (security boundary).
- Git errors → `ok=False`, sanitized stderr + hint.
- File writes are atomic (write tmp file via `tempfile.NamedTemporaryFile` then `os.replace`) to avoid corruption on crash.

## Security

- `project_root` boundary enforced on every path argument via `Path.resolve()` + `is_relative_to()`; reject paths resolving outside.
- Tokens never logged; redaction applied to any error surface that could include them.
- No shell-string concatenation for subprocess invocation — use `subprocess.run([...], shell=False)` with argv lists.
- ZIP extraction checks for path traversal (`..`) and absolute paths in archive entries before writing any file.

## Testing

- **Unit tests** per tool against fixture `.tex` files (good and intentionally broken).
- **Capability detection tests** with mocked binary absence (fake `PATH`).
- **Golden corpus** of 3–5 real-world project types (thesis, journal article, beamer deck, report with bib, multi-file book) — every read/lint/format tool must run clean against these.
- **No live Overleaf API in CI.** Sync is covered by a scripted manual smoke test using a scratch Overleaf project; documented in `CONTRIBUTING.md`.

## Distribution

- Published to PyPI as `overleaf-mcp`. Invoked in MCP client config via `uvx overleaf-mcp` or `pipx run overleaf-mcp`.
- No bundled TeX binaries — users install `latexindent`/`chktex`/`latexmk` via their OS package manager or TeX distribution.
- README includes: install steps per OS, MCP client config snippets (Claude Code, Copilot, Antigravity), free-tier ZIP workflow, Premium git workflow.

## Open questions

None blocking. Package naming on PyPI (`overleaf-mcp`) to be verified at publish time.
