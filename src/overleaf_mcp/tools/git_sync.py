"""Overleaf git sync tools: pull, push, status."""
import os
import subprocess
from pathlib import Path
from typing import Any

from overleaf_mcp.security.askpass import git_auth_env
from overleaf_mcp.security.redact import redact
from overleaf_mcp.types import ToolResult, fail, ok


def _run_git(
    args: list[str], cwd: Path, token: str | None = None
) -> tuple[int, str, str]:
    if token is not None:
        with git_auth_env(token) as env:
            result = subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
    else:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    return (
        result.returncode,
        redact(result.stdout, token),
        redact(result.stderr, token),
    )


def _is_repo(root: Path) -> bool:
    return (root / ".git").is_dir()


def pull_from_overleaf(
    project_root: Path, git_url: str, git_token: str
) -> ToolResult[dict[str, Any]]:
    if not _is_repo(project_root):
        code, out, err = _run_git(["clone", git_url, "."], project_root, git_token)
        if code != 0:
            return fail(f"git clone failed: {err}")
        return ok({"action": "clone", "stdout": out})
    code, out, err = _run_git(["pull", "--rebase"], project_root, git_token)
    if code != 0:
        return fail(f"git pull failed: {err}", "Resolve conflicts, then retry.")
    return ok({"action": "pull", "stdout": out})


def push_to_overleaf(
    project_root: Path, git_url: str, git_token: str, message: str
) -> ToolResult[dict[str, Any]]:
    if not _is_repo(project_root):
        return fail("project root is not a git repo; call pull_from_overleaf first")
    code, _, err = _run_git(["add", "-A"], project_root)
    if code != 0:
        return fail(f"git add failed: {err}")
    code, _, _ = _run_git(["diff", "--cached", "--quiet"], project_root)
    if code == 0:
        return ok({"pushed": False, "stdout": "no changes to push"})
    code, _, err = _run_git(
        ["-c", "user.email=overleaf-mcp@local", "-c", "user.name=overleaf-mcp",
         "commit", "-m", message],
        project_root,
    )
    if code != 0:
        return fail(f"git commit failed: {err}")
    code, out, err = _run_git(["push"], project_root, git_token)
    if code != 0:
        return fail(f"git push failed: {err}")
    return ok({"pushed": True, "stdout": out})


def overleaf_status(project_root: Path) -> ToolResult[dict[str, Any]]:
    if not _is_repo(project_root):
        return fail("project root is not a git repo")

    code_s, out_s, _ = _run_git(["status", "--porcelain"], project_root)
    code_b, out_b, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], project_root)
    code_ab, out_ab, _ = _run_git(
        ["rev-list", "--left-right", "--count", "HEAD...@{u}"], project_root
    )
    ahead = behind = 0
    if code_ab == 0:
        parts = out_ab.strip().split()
        if len(parts) >= 2:
            try:
                ahead, behind = int(parts[0]), int(parts[1])
            except ValueError:
                pass
    changed = [line[3:] for line in out_s.splitlines() if line.strip()]
    return ok(
        {
            "dirty": len(changed) > 0,
            "branch": out_b.strip() if code_b == 0 else None,
            "ahead": ahead,
            "behind": behind,
            "changed_files": changed,
        }
    )
