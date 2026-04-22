"""Cross-file style consistency checks."""
import re
from collections import Counter
from pathlib import Path

from overleaf_mcp.checks.findings import Finding
from overleaf_mcp.parse import Command, tokenize
from overleaf_mcp.tools.files import list_tex_files
from overleaf_mcp.types import ToolResult, ok

_SECTION_CMDS = {"section", "subsection", "subsubsection", "chapter"}
_ASCII_QUOTE_RE = re.compile(r'(?<!\\)"[^"\n]+"')
_RANGE_RE = re.compile(r"\b\d+-\d+\b")


def _classify_case(title: str) -> str:
    words = title.split()
    if len(words) < 2:
        return "mixed"
    capped = sum(1 for w in words if w and w[0].isupper())
    if capped == len(words):
        return "title"
    if capped <= 1:
        return "sentence"
    return "mixed"


def check_consistency(project_root: Path) -> ToolResult[list[dict]]:
    list_r = list_tex_files(project_root)
    if not list_r.ok:
        return list_r

    findings: list[Finding] = []
    headings: list[dict] = []

    for rel in [f for f in list_r.data if f.endswith(".tex")]:
        content = (project_root / rel).read_text(encoding="utf-8")
        for tok in tokenize(content):
            if isinstance(tok, Command) and tok.name in _SECTION_CMDS and tok.arg:
                headings.append(
                    {"file": rel, "line": tok.line, "title": tok.arg, "style": _classify_case(tok.arg)}
                )
        for i, line in enumerate(content.splitlines(), 1):
            if _ASCII_QUOTE_RE.search(line):
                findings.append(Finding(file=rel, line=i, code="CONS_ASCII_QUOTES",
                    message='use `` and \'\' instead of ASCII "..."', severity="info"))
            if _RANGE_RE.search(line):
                findings.append(Finding(file=rel, line=i, code="CONS_DASH_STYLE",
                    message="use -- (en-dash) for numeric ranges, not -", severity="info"))

    styles = {h["style"] for h in headings if h["style"] != "mixed"}
    if len(styles) > 1:
        counts = Counter(h["style"] for h in headings)
        dominant = counts.most_common(1)[0][0]
        for h in headings:
            if h["style"] not in (dominant, "mixed"):
                findings.append(
                    Finding(
                        file=h["file"], line=h["line"], code="CONS_HEADING_CASE",
                        message=f'heading "{h["title"]}" uses {h["style"]} case; dominant is {dominant}',
                        severity="info",
                    )
                )

    return ok([f.to_dict() for f in findings])
