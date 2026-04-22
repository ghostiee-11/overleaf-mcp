# overleaf-mcp: end-to-end demo

Each block below is a **real invocation** via `claude -p` against Claude Code + the installed MCP server, talking to a live Overleaf account. Agent-chosen tool calls; output unedited.

---

## 1. Discover available tools

```console
$ claude -p "Use the overleaf MCP. Call detect_capabilities and report one line
per tool in the format: 'name: available|missing' (plus the version if available)." \
  --allowedTools "mcp__overleaf__detect_capabilities"

- latexindent: missing
- chktex: missing
- latexmk: missing
- ols: available (ols, version 1.2.0)
```

Graceful degrade: tools that need latexindent/chktex/latexmk return an install hint when called; the rest work regardless.

---

## 2. List your Overleaf projects (free-tier API)

```console
$ claude -p "Use the overleaf MCP. Call olsync_list_projects. Format output as
a markdown table with columns: Project | ID | Access." \
  --allowedTools "mcp__overleaf__olsync_list_projects"
```

| Project        | ID                          | Access |
|---|---|---|
| My Thesis      | aaaaaaaaaaaaaaaaaaaaaaaa    | owner  |
| Paper Draft    | bbbbbbbbbbbbbbbbbbbbbbbb    | owner  |
| CV             | cccccccccccccccccccccccc    | owner  |

> Example data. Real output shows each of your Overleaf projects by name and ID.

Hits Overleaf's `/user/projects` JSON endpoint: no Premium needed, no scraping.

---

## 3. Full static-check sweep on a broken file

Seed file (deliberately broken. 7 distinct problems):

```tex
\documentclass{article}
\usepackage{subfig}
\usepackage{subcaption}
\begin{document}
\section{Demo}
\label{sec:intro}
See page 5-10 for details.
Bad math: $\left( x - 1 )$.
\begin{figure}
\includegraphics{missing.png}
\end{figure}
Cited: \cite{used}.
\bibliography{refs}
\end{document}
```

```console
$ claude -p "Use the overleaf MCP. Run a full check on main.tex: check_math,
check_figures, check_packages on main.tex, plus check_consistency and
find_unused_labels_and_refs on the project. For each finding report just:
code, one-line description. Group by tool." \
  --allowedTools "mcp__overleaf__check_math,mcp__overleaf__check_figures,\
mcp__overleaf__check_packages,mcp__overleaf__check_consistency,\
mcp__overleaf__find_unused_labels_and_refs"
```

**Output (agent-formatted):**

```
### check_math (main.tex)
- MATH_LEFT_RIGHT_UNPAIRED: \left (1) without matching \right at line 8
- MATH_BRACKET_UNBALANCED: unbalanced parens (0 open / 1 close) at line 8

### check_figures (main.tex)
- FIG_NO_CAPTION: figure missing \caption at line 9
- FIG_NO_LABEL: figure missing \label at line 9
- FIG_NO_CENTERING: figure missing \centering at line 9
- FIG_NO_FLOAT_SPEC: figure missing float placement like [htbp] at line 9

### check_packages (main.tex)
- PKG_CONFLICT: subfig and subcaption conflict; prefer subcaption at line 3

### check_consistency (project)
- CONS_DASH_STYLE: use -- (en-dash) for numeric ranges, not - at main.tex:7

### find_unused_labels_and_refs (project)
- LABEL_UNUSED: \label{sec:intro} never referenced at main.tex:6
- BIB_UNUSED: bib entry orphan_entry never cited at refs.bib:2
```

10 findings from 5 tools in one agent turn.

---

## 4. LaTeX log error translation

```console
$ claude -p "Use the overleaf MCP. Call explain_log with this log text:
'./main.tex:12: Undefined control sequence.
l.12 \\mycustom
./main.tex:20: Missing \$ inserted.
Overfull \\hbox (15.0pt too wide) in paragraph at lines 30--32'.
Return a compact markdown summary: count of errors and warnings, each with
file:line and a one-line suggestion." \
  --allowedTools "mcp__overleaf__explain_log"
```

**Output:**

```
## LaTeX Log Summary

Errors: 2 · Warnings: 1

### Errors
- ./main.tex:12. Undefined control sequence (\mycustom): typo or missing
  \usepackage; check spelling or add the defining package to the preamble.
- ./main.tex:20. Missing $ inserted: math used in text mode; wrap the
  expression in $...$ or \(...\) (often caused by _ / ^ outside math).

### Warnings
- ./main.tex:30–32. Overfull \hbox (15.0pt too wide): line doesn't fit;
  rephrase, allow hyphenation (\-), or use \sloppy / adjust margins.
```

No latexmk needed; pure-parser tool that works on any LaTeX log text.

---

## 5. Autonomous fix: agent chooses tools, reads, writes

The highlight. Agent decides which tools to call, reads the file, writes a
fixed version.

```console
$ claude -p "Use the overleaf MCP. The file main.tex has several LaTeX
issues. YOUR JOB: (1) call check_math, check_figures, check_packages on
main.tex to find issues, (2) read the file with read_tex_file, (3) write a
fixed version using write_tex_file that addresses every finding. Keep the
same document title/section. Don't change the bibliography. Respond ONLY
with a one-sentence summary of what you fixed." \
  --allowedTools "mcp__overleaf__check_math,mcp__overleaf__check_figures,\
mcp__overleaf__check_packages,mcp__overleaf__read_tex_file,\
mcp__overleaf__write_tex_file"
```

**Output:**

```
Fixed the unbalanced \left( by adding \right), removed the conflicting subfig
package (kept subcaption), added graphicx, and gave the figure [htbp]
placement, \centering, a \caption, and a \label.
```

**main.tex on disk after the agent's fix:**

```tex
\documentclass{article}
\usepackage{subcaption}
\usepackage{graphicx}
\begin{document}
\section{Demo}
\label{sec:intro}
See page 5-10 for details.
Bad math: $\left( x - 1 \right)$.
\begin{figure}[htbp]
\centering
\includegraphics{missing.png}
\caption{Demo figure.}
\label{fig:demo}
\end{figure}
Cited: \cite{used}.
\bibliography{refs}
\end{document}
```

---

## 6. Re-check to confirm the fix

```console
$ claude -p "Use the overleaf MCP. Run check_math, check_figures, and
check_packages on main.tex. For each tool, report: tool_name: OK | <codes>." \
  --allowedTools "mcp__overleaf__check_math,mcp__overleaf__check_figures,\
mcp__overleaf__check_packages"

- check_math: OK
- check_figures: OK
- check_packages: OK
```

All green.

---

## 7. Push to Overleaf, verify on server

```console
$ claude -p "Use the overleaf MCP to call olsync_push on
project_name='test_project_mcp'. Report: success flag, files_uploaded count." \
  --allowedTools "mcp__overleaf__olsync_push"

- success: true (ok: true)
- files_uploaded: 2 (main.tex, refs.bib)
```

**Independent verification**: re-download the project from Overleaf's server
(via the documented `/project/{id}/download/zip` endpoint, not the MCP) and
inspect the content:

```
Files on Overleaf server: ['main.tex', 'refs.bib']
main.tex has \right):  True
main.tex has \centering: True
main.tex removed subfig:  True
all agent fixes on server: True
```

The agent's changes are visible in the Overleaf web UI at
`https://www.overleaf.com/project/<your-project-id>`.

---

## Round-trip summary

```
User in Claude Code            overleaf-mcp                 Overleaf
──────────────────             ────────────                 ────────
"Fix my project"     ──►       olsync_pull    ──────GET────►  zip download
                               unzip locally
                               check_math ┐
                               check_figures ├── all pure Python
                               check_packages┘
                               read_tex_file
                               write_tex_file (atomic)
                               olsync_push    ──────POST───►  upload (×N)
"✅ fixed"           ◄──                     ◄────200────── entity_id
```

Same URL, same collaborators, no Premium, no git token, no zip shuffle.
