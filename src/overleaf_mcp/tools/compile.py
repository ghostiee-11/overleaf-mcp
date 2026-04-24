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

    # We deliberately omit -halt-on-error. With nonstopmode latexmk still exits with
    # non-zero on errors, but allows pdflatex to finish the run and write a complete
    # .log file that explain_log can parse. With -halt-on-error, pdflatex can abort
    # before the log is fully flushed on some platforms (observed on Ubuntu TeX Live).
    result = subprocess.run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-file-line-error",
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
    file_log = ""
    if log_path.exists():
        try:
            file_log = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    # Feed both the .log file AND the subprocess stdout/stderr to the parser.
    # On some TeX Live builds (observed on ubuntu-latest CI) latexmk surfaces
    # error context on stdout rather than flushing it all into the .log file,
    # so parsing only the .log can leave us with a successful-looking exit
    # but empty errors list.
    parse_input = (
        (file_log or "")
        + "\n"
        + (result.stdout or "")
        + "\n"
        + (result.stderr or "")
    )
    parsed = explain_log(parse_input)
    if not parsed.ok:
        return fail("log parse failed")

    success = result.returncode == 0
    raw_log = file_log or parse_input
    data: dict[str, Any] = {
        "success": success,
        "errors": parsed.data["errors"],
        "warnings": parsed.data["warnings"],
        "raw_log": raw_log,
    }
    if success:
        data["pdf_path"] = f".build/{base}.pdf"
    return ok(data)
