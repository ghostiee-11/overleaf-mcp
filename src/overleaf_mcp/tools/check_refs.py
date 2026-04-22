"""Detect dangling \\ref, unused \\label, and uncited bib entries."""
import re
from pathlib import Path

from overleaf_mcp.checks.findings import Finding
from overleaf_mcp.tools.files import list_tex_files
from overleaf_mcp.types import ToolResult, ok

_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
_REF_RE = re.compile(r"\\(?:ref|eqref|pageref|cref|Cref|autoref)\{([^}]+)\}")
_CITE_RE = re.compile(r"\\(?:cite|citep|citet|parencite|textcite)\{([^}]+)\}")


def find_unused_labels_and_refs(project_root: Path) -> ToolResult[list[dict]]:
    list_r = list_tex_files(project_root)
    if not list_r.ok:
        return list_r

    findings: list[Finding] = []
    labels: dict[str, dict] = {}
    refs: dict[str, list[dict]] = {}
    cites: set[str] = set()

    for rel in [f for f in list_r.data if f.endswith(".tex")]:
        content = (project_root / rel).read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            for m in _LABEL_RE.finditer(line):
                labels[m.group(1)] = {"file": rel, "line": i}
            for m in _REF_RE.finditer(line):
                for key in [k.strip() for k in m.group(1).split(",")]:
                    refs.setdefault(key, []).append({"file": rel, "line": i})
            for m in _CITE_RE.finditer(line):
                for key in [k.strip() for k in m.group(1).split(",")]:
                    cites.add(key)

    for key, occs in refs.items():
        if key not in labels:
            for occ in occs:
                findings.append(
                    Finding(
                        file=occ["file"], line=occ["line"], code="REF_DANGLING",
                        message=f"\\ref{{{key}}} has no matching \\label{{{key}}}",
                        severity="error",
                    )
                )

    for key, pos in labels.items():
        if key not in refs:
            findings.append(
                Finding(
                    file=pos["file"], line=pos["line"], code="LABEL_UNUSED",
                    message=f"\\label{{{key}}} is never referenced", severity="info",
                )
            )

    bib_keys: dict[str, dict] = {}
    for rel in [f for f in list_r.data if f.endswith(".bib")]:
        content = (project_root / rel).read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            m = re.match(r"^@\w+\s*\{\s*([^,\s]+)", line)
            if m:
                bib_keys[m.group(1)] = {"file": rel, "line": i}
    for key, pos in bib_keys.items():
        if key not in cites:
            findings.append(
                Finding(
                    file=pos["file"], line=pos["line"], code="BIB_UNUSED",
                    message=f'bib entry "{key}" is never cited', severity="info",
                )
            )

    return ok([f.to_dict() for f in findings])
