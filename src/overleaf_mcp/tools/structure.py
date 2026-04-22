"""Detect project main file, sections, bib, inputs, classes."""
import re
from pathlib import Path
from typing import Any

from overleaf_mcp.parse import Command, tokenize
from overleaf_mcp.tools.files import list_tex_files
from overleaf_mcp.types import ToolResult, ok

_SECTION_CMDS = {"part", "chapter", "section", "subsection", "subsubsection"}
_TEX_ROOT_RE = re.compile(r"%\s*!TeX\s+root\s*=\s*(\S+)", re.IGNORECASE)


def get_project_structure(project_root: Path) -> ToolResult[dict[str, Any]]:
    list_r = list_tex_files(project_root)
    if not list_r.ok:
        return list_r

    files = list_r.data
    tex_files = [f for f in files if f.endswith(".tex")]

    main_file: str | None = None
    for rel in tex_files:
        content = (project_root / rel).read_text(encoding="utf-8")
        m = _TEX_ROOT_RE.search(content)
        if m:
            main_file = m.group(1)
            break
    if main_file is None:
        for rel in tex_files:
            if "\\documentclass" in (project_root / rel).read_text(encoding="utf-8"):
                main_file = rel
                break

    sections: list[dict[str, Any]] = []
    bib_files: list[str] = []
    inputs: list[str] = []
    class_files = [f for f in files if f.endswith((".cls", ".sty"))]

    for rel in tex_files:
        content = (project_root / rel).read_text(encoding="utf-8")
        for tok in tokenize(content):
            if not isinstance(tok, Command):
                continue
            if tok.name in _SECTION_CMDS and tok.arg is not None:
                sections.append(
                    {"level": tok.name, "title": tok.arg, "file": rel, "line": tok.line}
                )
            elif tok.name in ("input", "include") and tok.arg:
                inputs.append(tok.arg)
            elif tok.name in ("bibliography", "addbibresource") and tok.arg:
                bib_files.append(tok.arg if tok.arg.endswith(".bib") else f"{tok.arg}.bib")

    return ok(
        {
            "main_file": main_file,
            "sections": sections,
            "bib_files": bib_files,
            "class_files": class_files,
            "inputs": inputs,
        }
    )
