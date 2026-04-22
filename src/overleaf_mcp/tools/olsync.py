"""Thin wrappers around `overleaf-sync` (`ols`) for free-tier bi-directional sync."""
import shutil
import subprocess
from pathlib import Path
from typing import Any

from overleaf_mcp.capability import detect_capabilities
from overleaf_mcp.types import ToolResult, fail, ok


def _ensure_ols() -> ToolResult[bool]:
    caps = detect_capabilities()
    if caps["ols"].available:
        return ok(True)
    return fail("overleaf-sync (ols) not installed", caps["ols"].suggestion)


def _base_args(
    project_root: Path,
    project_name: str | None,
    cookie_path: str | None,
) -> list[str]:
    args: list[str] = ["-p", str(project_root)]
    if project_name:
        args += ["-n", project_name]
    if cookie_path:
        args += ["--store-path", cookie_path]
    return args


def _run_ols(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    result = subprocess.run(
        ["ols", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def olsync_list_projects(
    cookie_path: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Return the list of Overleaf projects available to the logged-in account."""
    chk = _ensure_ols()
    if not chk.ok:
        return chk
    args = ["list"]
    if cookie_path:
        args += ["--store-path", cookie_path]
    code, out, err = _run_ols(args)
    if code != 0:
        return fail(
            f"ols list failed: {err.strip() or out.strip()}",
            "Run `ols login` once to authenticate, then retry.",
        )
    projects = [line.strip() for line in out.splitlines() if line.strip()]
    return ok({"projects": projects})


def olsync_pull(
    project_root: Path,
    project_name: str | None = None,
    cookie_path: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Pull the remote Overleaf project into `project_root` (one-way, remote → local)."""
    chk = _ensure_ols()
    if not chk.ok:
        return chk
    args = _base_args(project_root, project_name, cookie_path) + ["--remote-only"]
    code, out, err = _run_ols(args, timeout=120)
    if code != 0:
        return fail(
            f"ols pull failed: {err.strip() or out.strip()}",
            "If not authenticated, run `ols login`. If the project name is wrong, "
            "pass `project_name` or set OVERLEAF_PROJECT_NAME.",
        )
    return ok({"action": "pull", "stdout": out.strip()})


def olsync_push(
    project_root: Path,
    project_name: str | None = None,
    cookie_path: str | None = None,
) -> ToolResult[dict[str, Any]]:
    """Push local project_root changes to the Overleaf project (one-way, local → remote)."""
    chk = _ensure_ols()
    if not chk.ok:
        return chk
    args = _base_args(project_root, project_name, cookie_path) + ["--local-only"]
    code, out, err = _run_ols(args, timeout=120)
    if code != 0:
        return fail(
            f"ols push failed: {err.strip() or out.strip()}",
            "If not authenticated, run `ols login`. Make sure the project name "
            "matches an existing Overleaf project (create it on Overleaf first).",
        )
    return ok({"action": "push", "stdout": out.strip()})


def olsync_login_instructions() -> ToolResult[dict[str, Any]]:
    """Return manual login steps (login is interactive, not automatable)."""
    ols_path = shutil.which("ols")
    return ok(
        {
            "instructions": [
                "1. Open a terminal (any terminal, not inside Claude Code).",
                "2. Run: ols login",
                "3. A browser window opens. Sign into your Overleaf account.",
                "4. The cookie is stored at ./.olauth (or wherever you pass --path).",
                "5. Come back here and call olsync_pull or olsync_push.",
            ],
            "ols_binary_path": ols_path,
            "note": (
                "Login is interactive and cannot be driven by this MCP. Run it once in your "
                "own terminal; the MCP then reuses the stored cookie."
            ),
        }
    )
