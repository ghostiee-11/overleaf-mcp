"""Static checks for package conflicts, duplicates, load order, and missing deps."""
import re

from overleaf_mcp.checks.findings import Finding
from overleaf_mcp.types import ToolResult, ok

_USEPKG_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")
_CMD_RE = re.compile(r"\\([a-zA-Z]+)\b")

_CONFLICTS: list[tuple[str, str, str]] = [
    ("subfig", "subcaption", "subfig and subcaption conflict; prefer subcaption"),
]
_LOAD_ORDER: list[tuple[str, str]] = [
    ("hyperref", "cleveref"),
]
_CMD_PACKAGE: dict[str, str] = {
    "SI": "siunitx",
    "si": "siunitx",
    "toprule": "booktabs",
    "midrule": "booktabs",
    "bottomrule": "booktabs",
    "subfloat": "subfig",
}


def check_packages(file: str, content: str) -> ToolResult[list[dict]]:
    findings: list[Finding] = []
    loaded: dict[str, int] = {}
    for i, line in enumerate(content.splitlines(), 1):
        m = _USEPKG_RE.search(line)
        if not m:
            continue
        for pkg in [p.strip() for p in m.group(1).split(",")]:
            if pkg in loaded:
                findings.append(
                    Finding(
                        file=file, line=i, code="PKG_DUPLICATE",
                        message=f'package "{pkg}" loaded twice (first on line {loaded[pkg]})',
                        severity="warning",
                    )
                )
            else:
                loaded[pkg] = i

    for a, b, msg in _CONFLICTS:
        if a in loaded and b in loaded:
            findings.append(
                Finding(file=file, line=max(loaded[a], loaded[b]), code="PKG_CONFLICT",
                    message=msg, severity="error")
            )

    for before, after in _LOAD_ORDER:
        b_line = loaded.get(before)
        a_line = loaded.get(after)
        if b_line is not None and a_line is not None and b_line > a_line:
            findings.append(
                Finding(
                    file=file, line=b_line, code="PKG_LOAD_ORDER",
                    message=f'"{before}" should be loaded before "{after}"',
                    severity="warning",
                )
            )

    used = set(_CMD_RE.findall(content))
    for cmd, pkg in _CMD_PACKAGE.items():
        if cmd in used and pkg not in loaded:
            findings.append(
                Finding(
                    file=file, line=1, code="PKG_MISSING_FOR_CMD",
                    message=f'command \\{cmd} is used but package "{pkg}" is not loaded',
                    severity="warning",
                )
            )

    return ok([f.to_dict() for f in findings])
