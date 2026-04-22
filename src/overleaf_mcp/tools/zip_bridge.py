"""Bidirectional ZIP bridge for Overleaf free-tier round-trip."""
import os
import zipfile
from pathlib import Path
from typing import Any

from overleaf_mcp.types import ToolResult, fail, ok

_EXCLUDE_DIRS = {".git", ".build", "node_modules", "__pycache__", ".venv"}


def _is_inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def import_overleaf_zip(
    project_root: Path, zip_path: Path
) -> ToolResult[dict[str, int]]:
    abs_root = Path(project_root).resolve()
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as err:
        return fail(f"invalid zip: {err}")
    try:
        # Pre-validate every entry before writing anything
        for info in zf.infolist():
            name = info.filename
            if name.startswith("/") or Path(name).is_absolute():
                return fail(f"zip contains absolute path: {name}")
            target = (abs_root / name).resolve()
            if not _is_inside(abs_root, target):
                return fail(f"zip contains path escaping project root: {name}")

        count = 0
        for info in zf.infolist():
            target = (abs_root / info.filename).resolve()
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            count += 1
        return ok({"files_extracted": count})
    finally:
        zf.close()


def export_overleaf_zip(
    project_root: Path, out_path: Path
) -> ToolResult[dict[str, Any]]:
    abs_root = Path(project_root).resolve()
    entries = 0
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, dirnames, filenames in os.walk(abs_root):
                dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
                for name in filenames:
                    abs_path = Path(dirpath) / name
                    rel = str(abs_path.relative_to(abs_root).as_posix())
                    zf.write(abs_path, rel)
                    entries += 1
        size = out_path.stat().st_size
        return ok({"bytes": size, "entries": entries})
    except OSError as err:
        return fail(f"export failed: {err}")
