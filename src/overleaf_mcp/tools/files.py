"""File I/O tools."""
import os
import tempfile
from pathlib import Path
from typing import Any

from overleaf_mcp.security.paths import resolve_inside_root
from overleaf_mcp.types import ToolResult, fail, ok

_TEX_EXT = {".tex", ".bib", ".cls", ".sty"}
_SKIP_DIRS = {"node_modules", ".git", ".build", "__pycache__", ".venv"}


def _count_lines(content: str) -> int:
    if not content:
        return 0
    return content.count("\n") + (0 if content.endswith("\n") else 1)


def list_tex_files(project_root: Path) -> ToolResult[list[str]]:
    root = Path(project_root).resolve()
    if not root.is_dir():
        return fail(f"not a directory: {root}")
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in _SKIP_DIRS]
        for name in filenames:
            if Path(name).suffix.lower() in _TEX_EXT:
                rel = str(Path(dirpath, name).relative_to(root).as_posix())
                files.append(rel)
    return ok(files)


def read_tex_file(project_root: Path, rel_path: str) -> ToolResult[dict[str, Any]]:
    resolved = resolve_inside_root(project_root, rel_path)
    if not resolved.ok:
        return resolved
    try:
        content = resolved.data.read_text(encoding="utf-8")
    except OSError as err:
        return fail(f"failed to read: {err}")
    return ok({"content": content, "lines": _count_lines(content)})


def write_tex_file(
    project_root: Path, rel_path: str, content: str
) -> ToolResult[dict[str, int]]:
    resolved = resolve_inside_root(project_root, rel_path)
    if not resolved.ok:
        return resolved
    target: Path = resolved.data
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8")
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=target.name + ".tmp-", dir=str(target.parent)
    )
    try:
        with os.fdopen(tmp_fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp_path, target)
    except OSError as err:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return fail(f"failed to write: {err}")
    return ok({"bytes": len(data)})
