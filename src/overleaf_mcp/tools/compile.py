"""Run latexmk and translate its log into structured errors."""
import subprocess
from pathlib import Path
from typing import Any

from overleaf_mcp.capability import detect_capabilities
from overleaf_mcp.security.paths import resolve_inside_root
from overleaf_mcp.tools.explain_log import explain_log
from overleaf_mcp.types import ToolResult, fail, ok


def compile_file(project_root: Path, rel_path: str) -> ToolResult[dict[str, Any]]:
    caps = detect_capabilities()
    if not caps["latexmk"].available:
        return fail("latexmk not installed", caps["latexmk"].suggestion)
    resolved = resolve_inside_root(project_root, rel_path)
    if not resolved.ok:
        return resolved
    target: Path = resolved.data

    out_dir = project_root / ".build"
    out_dir.mkdir(exist_ok=True)

    result = subprocess.run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-file-line-error",
            "-halt-on-error",
            f"-outdir={out_dir}",
            str(target),
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    base = target.stem
    log_path = out_dir / f"{base}.log"
    raw_log = ""
    if log_path.exists():
        try:
            raw_log = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    if not raw_log:
        raw_log = (result.stdout or "") + "\n" + (result.stderr or "")

    parsed = explain_log(raw_log)
    if not parsed.ok:
        return fail("log parse failed")

    success = result.returncode == 0
    data: dict[str, Any] = {
        "success": success,
        "errors": parsed.data["errors"],
        "warnings": parsed.data["warnings"],
        "raw_log": raw_log,
    }
    if success:
        data["pdf_path"] = f".build/{base}.pdf"
    return ok(data)
