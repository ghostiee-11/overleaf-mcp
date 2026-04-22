"""Load runtime configuration from environment variables."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from overleaf_mcp.types import ToolResult, fail, ok

Mode = Literal["local", "synced"]


@dataclass(frozen=True)
class Config:
    mode: Mode
    project_root: Path
    git_url: str | None
    git_token: str | None
    ols_project_name: str | None
    ols_cookie_path: str | None


def load_config(env: Mapping[str, str]) -> ToolResult[Config]:
    project_root = env.get("OVERLEAF_PROJECT_ROOT")
    if not project_root:
        return fail(
            "OVERLEAF_PROJECT_ROOT is required",
            "Set it in your MCP client config to an absolute path.",
        )
    root = Path(project_root).resolve()
    if not root.is_dir():
        return fail(f"project root does not exist or is not a directory: {root}")
    git_url = env.get("OVERLEAF_GIT_URL") or None
    git_token = env.get("OVERLEAF_GIT_TOKEN") or None
    ols_project_name = env.get("OVERLEAF_PROJECT_NAME") or None
    ols_cookie_path = env.get("OVERLEAF_OLS_COOKIE") or None
    mode: Mode = "synced" if (git_url and git_token) else "local"
    return ok(
        Config(
            mode=mode,
            project_root=root,
            git_url=git_url,
            git_token=git_token,
            ols_project_name=ols_project_name,
            ols_cookie_path=ols_cookie_path,
        )
    )
