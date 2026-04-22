"""Enforce that every resolved path lives under the project root."""
from pathlib import Path

from overleaf_mcp.types import ToolResult, fail, ok


def resolve_inside_root(root: Path | str, path: str) -> ToolResult[Path]:
    abs_root = Path(root).resolve()
    candidate = Path(path)
    candidate = (candidate if candidate.is_absolute() else abs_root / candidate).resolve()
    try:
        candidate.relative_to(abs_root)
    except ValueError:
        return fail(f"path outside project root: {path}")
    return ok(candidate)
