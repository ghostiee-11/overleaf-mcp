"""Lint LaTeX files via `chktex`."""
import subprocess
from pathlib import Path
from typing import Any

from overleaf_mcp.capability import detect_capabilities
from overleaf_mcp.security.paths import resolve_inside_root
from overleaf_mcp.types import ToolResult, fail, ok


def lint_file(project_root: Path, rel_path: str) -> ToolResult[dict[str, Any]]:
    caps = detect_capabilities()
    cap = caps["chktex"]
    if not cap.available:
        return fail("chktex not installed", cap.suggestion)
    resolved = resolve_inside_root(project_root, rel_path)
    if not resolved.ok:
        return resolved
    target: Path = resolved.data
    fmt = "%f:%l:%c:%n:%m\n"
    result = subprocess.run(
        ["chktex", "-q", "-f", fmt, str(target)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    warnings: list[dict[str, Any]] = []
    for raw in result.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        parts = raw.split(":", 4)
        if len(parts) < 5:
            continue
        try:
            line = int(parts[1])
            column = int(parts[2])
        except ValueError:
            continue
        warnings.append(
            {
                "line": line,
                "column": column,
                "code": parts[3],
                "message": parts[4].strip(),
            }
        )
    return ok({"warnings": warnings})
