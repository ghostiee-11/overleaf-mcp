"""Format LaTeX files via `latexindent`."""
import difflib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from overleaf_mcp.capability import detect_capabilities
from overleaf_mcp.security.paths import resolve_inside_root
from overleaf_mcp.types import ToolResult, fail, ok


def _ensure_latexindent() -> ToolResult[bool]:
    caps = detect_capabilities()
    cap = caps["latexindent"]
    if not cap.available:
        return fail("latexindent not installed", cap.suggestion)
    return ok(True)


def _run_latexindent(input_path: Path) -> str:
    result = subprocess.run(
        ["latexindent", "-s", str(input_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout


def format_snippet(code: str) -> ToolResult[dict[str, str]]:
    chk = _ensure_latexindent()
    if not chk.ok:
        return chk
    fd, tmp_path = tempfile.mkstemp(suffix=".tex", prefix="olmcp-snippet-")
    try:
        os.close(fd)
        Path(tmp_path).write_text(code, encoding="utf-8")
        formatted = _run_latexindent(Path(tmp_path))
        return ok({"formatted": formatted})
    except subprocess.CalledProcessError as err:
        return fail(f"latexindent failed: {err.stderr or err.stdout}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def format_file(project_root: Path, rel_path: str) -> ToolResult[dict[str, bool]]:
    chk = _ensure_latexindent()
    if not chk.ok:
        return chk
    resolved = resolve_inside_root(project_root, rel_path)
    if not resolved.ok:
        return resolved
    target: Path = resolved.data
    try:
        before = target.read_text(encoding="utf-8")
        formatted = _run_latexindent(target)
        if formatted == before:
            return ok({"changed": False})
        fd, tmp_name = tempfile.mkstemp(
            prefix=target.name + ".tmp-", dir=str(target.parent)
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(formatted)
        os.replace(tmp_name, target)
        return ok({"changed": True})
    except subprocess.CalledProcessError as err:
        return fail(f"format failed: {err.stderr or err.stdout}")
    except OSError as err:
        return fail(f"format failed: {err}")


def check_formatting(
    project_root: Path, rel_path: str
) -> ToolResult[dict[str, Any]]:
    chk = _ensure_latexindent()
    if not chk.ok:
        return chk
    resolved = resolve_inside_root(project_root, rel_path)
    if not resolved.ok:
        return resolved
    target: Path = resolved.data
    try:
        before = target.read_text(encoding="utf-8")
        formatted = _run_latexindent(target)
        if formatted == before:
            return ok({"diff": "", "would_change": False})
        diff = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                formatted.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
                n=3,
            )
        )
        return ok({"diff": diff, "would_change": True})
    except subprocess.CalledProcessError as err:
        return fail(f"check failed: {err.stderr or err.stdout}")
    except OSError as err:
        return fail(f"check failed: {err}")
